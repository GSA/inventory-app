---
title: Restart Failure
labels: bug
---

Workflow with Issue: {{ workflow }}
Job Failed: {{ env.GITHUB_JOB }}
Last Commit: {{ env.LAST_COMMIT }}
Last run by: {{ env.LAST_RUN_BY }}
Most Recent Failure: https://github.com/GSA/inventory-app/actions/runs/{{ env.RUN_ID }}
