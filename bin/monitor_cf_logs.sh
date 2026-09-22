#!/bin/bash

set -euo pipefail

# Monitor Cloud Foundry task logs until the task exits.
#
# Usage: monitor_cf_logs.sh <app_name> <task_name> [warning_pattern]
#
# Exit codes:
#   0 - Cloud Foundry reports the task state as SUCCEEDED
#   1 - The task failed or its successful completion could not be verified
#
# If warning_pattern matches one or more log lines, writes
# "warning_pattern_matched" to .cf_monitor_result in GITHUB_WORKSPACE (or the
# current directory) so CI can branch on the result without changing the task
# exit status.

app_to_monitor=${1:?Usage: monitor_cf_logs.sh <app_name> <task_name> [warning_pattern]}
task_to_monitor=${2:?Usage: monitor_cf_logs.sh <app_name> <task_name> [warning_pattern]}
warning_pattern=${3:-}

poll_seconds=${CF_TASK_POLL_SECONDS:-5}
lookup_timeout_seconds=${CF_TASK_LOOKUP_TIMEOUT_SECONDS:-60}
max_poll_errors=${CF_TASK_MAX_POLL_ERRORS:-3}
terminal_log_settle_seconds=${CF_TASK_LOG_SETTLE_SECONDS:-2}
result_file="${GITHUB_WORKSPACE:-.}/.cf_monitor_result"
log_pid=""

rm -f "$result_file"

apk add --no-cache jq

write_warning_result() {
  echo "warning_pattern_matched" > "$result_file"
}

scan_task_logs() {
  local print_lines=$1
  local line

  while IFS= read -r line; do
    if [[ "$line" != *"[APP/TASK/${task_to_monitor}/0]"* ]]; then
      continue
    fi
    if [[ "$print_lines" == "true" ]]; then
      echo "$line"
    fi
    if [[ -n "$warning_pattern" && "$line" == *"$warning_pattern"* ]]; then
      write_warning_result
    fi
  done
}

stop_log_stream() {
  if [[ -n "$log_pid" ]]; then
    kill "$log_pid" 2>/dev/null || true
    wait "$log_pid" 2>/dev/null || true
    log_pid=""
  fi
}

scan_recent_logs_for_warning() {
  local recent_logs

  if [[ -z "$warning_pattern" || -f "$result_file" ]]; then
    return 0
  fi
  if ! recent_logs=$(cf logs "$app_to_monitor" --recent); then
    echo "Unable to inspect recent task logs for the warning pattern." >&2
    return 1
  fi
  scan_task_logs false <<<"$recent_logs"
}

print_recent_task_logs() {
  local recent_logs

  if [[ "$terminal_log_settle_seconds" -gt 0 ]]; then
    sleep "$terminal_log_settle_seconds"
  fi
  if ! recent_logs=$(cf logs "$app_to_monitor" --recent); then
    echo "Unable to inspect recent logs for failed task ${task_to_monitor}." >&2
    return 1
  fi
  scan_task_logs true <<<"$recent_logs"
}

poll_error() {
  local description=$1

  poll_errors=$((poll_errors + 1))
  if [[ "$poll_errors" -ge "$max_poll_errors" ]]; then
    echo "${description} after ${poll_errors} consecutive attempts." >&2
    return 1
  fi
  echo "${description}; retrying (${poll_errors}/${max_poll_errors})." >&2
  return 0
}

trap stop_log_stream EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cf logs "$app_to_monitor" > >(scan_task_logs true) &
log_pid=$!

app_guid=$(cf app "$app_to_monitor" --guid)
encoded_task_name=$(jq -rn --arg name "$task_to_monitor" '$name | @uri')
lookup_deadline=$((SECONDS + lookup_timeout_seconds))
task_guid=""
poll_errors=0

while [[ -z "$task_guid" ]]; do
  task_response=""
  if task_response=$(
    cf curl --fail \
      "/v3/apps/${app_guid}/tasks?names=${encoded_task_name}&order_by=-created_at&per_page=1"
  ); then
    poll_errors=0
    task_guid=$(
      jq -r --arg name "$task_to_monitor" \
        '.resources[] | select(.name == $name) | .guid' <<<"$task_response"
    )
  elif ! poll_error "Unable to look up Cloud Foundry task ${task_to_monitor}"; then
    exit 1
  fi

  if [[ -n "$task_guid" ]]; then
    break
  fi
  if [[ "$SECONDS" -ge "$lookup_deadline" ]]; then
    echo "Cloud Foundry task ${task_to_monitor} was not found within ${lookup_timeout_seconds} seconds." >&2
    exit 1
  fi
  sleep "$poll_seconds"
done

echo "Monitoring Cloud Foundry task ${task_to_monitor} (${task_guid})."
poll_errors=0
last_state=""
log_disconnect_reported=false

while true; do
  if [[ -n "$log_pid" && "$log_disconnect_reported" == false ]] &&
    ! kill -0 "$log_pid" 2>/dev/null; then
    wait "$log_pid" 2>/dev/null || true
    log_pid=""
    log_disconnect_reported=true
    echo "Cloud Foundry log stream ended; continuing to poll task state." >&2
  fi

  task_response=""
  task_state=""
  if task_response=$(cf curl --fail "/v3/tasks/${task_guid}") &&
    task_state=$(jq -er '.state' <<<"$task_response"); then
    poll_errors=0
  else
    if ! poll_error "Unable to read Cloud Foundry task ${task_to_monitor}"; then
      exit 1
    fi
    sleep "$poll_seconds"
    continue
  fi

  if [[ "$task_state" != "$last_state" ]]; then
    echo "Cloud Foundry task ${task_to_monitor} state: ${task_state}."
    last_state=$task_state
  fi

  case "$task_state" in
    SUCCEEDED)
      stop_log_stream
      if ! scan_recent_logs_for_warning; then
        exit 1
      fi
      exit 0
      ;;
    FAILED)
      stop_log_stream
      print_recent_task_logs || true
      exit 1
      ;;
    PENDING|RUNNING|CANCELING)
      ;;
    *)
      echo "Cloud Foundry task ${task_to_monitor} has unexpected state '${task_state}'." >&2
      exit 1
      ;;
  esac

  sleep "$poll_seconds"
done
