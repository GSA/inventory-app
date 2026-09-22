"""Tests for Inventory CKAN commands."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import ckan.model as model
import ckan.plugins.toolkit as toolkit
import ckan.tests.factories as factories

from ckanext.datagov_inventory import action, cli, user_activity


@pytest.mark.usefixtures('clean_db')
class TestDeleteInactiveUsers:
    now = datetime(2026, 9, 11, 12, 0, 0)

    @pytest.fixture(autouse=True)
    def _configure_inactivity_days(self, monkeypatch):
        monkeypatch.setitem(
            toolkit.config,
            cli.INACTIVITY_DAYS_CONFIG,
            '90',
        )

    def test_defaults_warning_days_when_config_is_null(self, monkeypatch):
        monkeypatch.setitem(
            toolkit.config,
            cli.INACTIVITY_WARNING_DAYS_CONFIG,
            None,
        )

        assert cli._inactivity_warning_days() == 7

    def _set_user_dates(self, user, created, last_active):
        user_obj = model.User.get(user['id'])
        user_obj.created = created
        user_obj.last_active = last_active
        model.Session.commit()
        return user_obj

    def test_deletes_users_with_old_last_active(self, monkeypatch):
        # A user past the inactivity cutoff is only warned on the first
        # run; deletion happens on a later run once the warning period
        # (default 7 days) has elapsed.
        current_time = [self.now]
        monkeypatch.setattr(cli, '_utcnow', lambda: current_time[0])
        inactive = factories.User(name='inactive')
        boundary = factories.User(name='boundary')
        recent = factories.User(name='recent')

        self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=100),
        )
        self._set_user_dates(
            boundary,
            self.now - timedelta(days=180),
            self.now - timedelta(days=90),
        )
        self._set_user_dates(
            recent,
            self.now - timedelta(days=180),
            self.now - timedelta(days=80),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        assert model.User.get(boundary['id']).state == model.State.ACTIVE
        assert model.User.get(recent['id']).state == model.State.ACTIVE
        assert 'Deleted 0 inactive user(s).' in result.output

        current_time[0] += timedelta(days=cli.INACTIVITY_WARNING_DAYS_DEFAULT)
        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        # boundary was exactly at the cutoff and also got warned on the
        # first run, so 7 days later it's overdue too.
        assert model.User.get(boundary['id']).state == model.State.DELETED
        assert model.User.get(recent['id']).state == model.State.ACTIVE
        assert 'Deleted 2 inactive user(s).' in result.output

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    @patch('ckanext.datagov_inventory.notifications.send_locked')
    def test_notifies_about_to_lock_and_locked_users(
        self,
        send_locked,
        send_about_to_lock,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        warning = factories.User(name='warning-user')
        locked = factories.User(name='locked-user')
        self._set_user_dates(
            warning,
            self.now - timedelta(days=180),
            self.now - timedelta(days=85),
        )
        self._set_user_dates(
            locked,
            self.now - timedelta(days=180),
            self.now - timedelta(days=91),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        send_about_to_lock.assert_any_call(
            model.User.get(warning['id']), 5
        )
        send_about_to_lock.assert_any_call(model.User.get(locked['id']), 7)
        assert send_about_to_lock.call_count == 2
        assert 'Sent warning email to warning-user' in result.output
        assert 'Sent warning email to locked-user' in result.output
        send_locked.assert_not_called()
        assert model.User.get(locked['id']).state == model.State.ACTIVE

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert send_about_to_lock.call_count == 2

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    @patch('ckanext.datagov_inventory.notifications.send_locked')
    def test_successful_warning_defers_overdue_deletion(
        self,
        send_locked,
        send_about_to_lock,
        monkeypatch,
    ):
        current_time = [self.now]
        monkeypatch.setattr(cli, '_utcnow', lambda: current_time[0])
        inactive = factories.User(name='warn-before-delete')
        self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=91),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        send_about_to_lock.assert_called_once_with(
            model.User.get(inactive['id']), 7
        )
        send_locked.assert_not_called()

        current_time[0] += timedelta(days=7)
        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        assert 'warn-before-delete is scheduled to be deleted on/after ' \
            in result.output
        assert 'warning sent:' in result.output
        send_locked.assert_called_once_with(model.User.get(inactive['id']))

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    def test_activity_after_warning_resets_schedule(
        self,
        send_about_to_lock,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        active_again = factories.User(name='active-again')
        user_obj = self._set_user_dates(
            active_again,
            self.now - timedelta(days=180),
            self.now - timedelta(days=100),
        )
        user_activity.set_inactivity_warning_sent_at(
            user_obj, self.now - timedelta(days=101)
        )
        model.Session.commit()

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert 'active-again was active again after warning' in result.output
        send_about_to_lock.assert_called_once_with(
            model.User.get(active_again['id']), 7
        )
        assert (
            user_activity.get_inactivity_warning_sent_at(
                model.User.get(active_again['id'])
            ) == self.now
        )

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    def test_dry_run_reports_activity_after_warning_without_resetting(
        self,
        send_about_to_lock,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        active_again = factories.User(name='active-again-dry-run')
        user_obj = self._set_user_dates(
            active_again,
            self.now - timedelta(days=180),
            self.now - timedelta(days=100),
        )
        warning_sent_at = self.now - timedelta(days=101)
        user_activity.set_inactivity_warning_sent_at(
            user_obj, warning_sent_at
        )
        model.Session.commit()

        result = CliRunner().invoke(
            cli.delete_inactive_users,
            ['--dry-run'],
        )

        assert result.exit_code == 0, result.output
        assert 'Would reset warning schedule for active-again-dry-run' in (
            result.output
        )
        send_about_to_lock.assert_not_called()
        assert (
            user_activity.get_inactivity_warning_sent_at(
                model.User.get(active_again['id'])
            ) == warning_sent_at
        )

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    @patch('ckanext.datagov_inventory.notifications.send_locked')
    def test_failed_warning_is_treated_as_success(
        self,
        send_locked,
        send_about_to_lock,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        send_about_to_lock.side_effect = RuntimeError('SMTP unavailable')
        inactive = factories.User(name='failed-warning')
        self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=91),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        send_about_to_lock.assert_called_once_with(
            model.User.get(inactive['id']), 7
        )
        send_locked.assert_not_called()
        assert (
            'Warning email delivery failed for failed-warning'
            in result.output
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        send_about_to_lock.assert_called_once()

    @patch('ckanext.datagov_inventory.notifications.send_about_to_lock')
    def test_dry_run_does_not_send_about_to_lock_email(
        self,
        send_about_to_lock,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        warning = factories.User(name='warning-dry-run')
        self._set_user_dates(
            warning,
            self.now - timedelta(days=180),
            self.now - timedelta(days=85),
        )

        result = CliRunner().invoke(
            cli.delete_inactive_users,
            ['--dry-run'],
        )

        assert result.exit_code == 0, result.output
        send_about_to_lock.assert_not_called()
        assert (
            'Would send warning email to warning-dry-run '
            '({}, 5 days until lock)'.format(warning['email'])
            in result.output
        )

    def test_uses_creation_date_when_last_active_is_null(self, monkeypatch):
        current_time = [self.now]
        monkeypatch.setattr(cli, '_utcnow', lambda: current_time[0])
        inactive = factories.User(name='never-active-old')
        recent = factories.User(name='never-active-recent')

        self._set_user_dates(
            inactive,
            self.now - timedelta(days=100),
            None,
        )
        self._set_user_dates(
            recent,
            self.now - timedelta(days=80),
            None,
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        assert model.User.get(recent['id']).state == model.State.ACTIVE
        assert (
            'never-active-old is scheduled to be deleted on/after '
            in result.output
        )
        assert 'created:' in result.output

        current_time[0] += timedelta(days=cli.INACTIVITY_WARNING_DAYS_DEFAULT)
        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        assert model.User.get(recent['id']).state == model.State.ACTIVE

    def test_dry_run_does_not_delete_users(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        inactive = factories.User(name='inactive-dry-run')
        self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=91),
        )

        result = CliRunner().invoke(
            cli.delete_inactive_users,
            ['--dry-run'],
        )

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        assert (
            'Would send warning email to inactive-dry-run '
            '({}, 7 days until lock)'.format(inactive['email'])
            in result.output
        )
        assert 'Would delete inactive-dry-run' not in result.output
        assert 'Would delete 0 inactive user(s).' in result.output

    def test_soft_delete_retains_organization_membership(self, monkeypatch):
        current_time = [self.now]
        monkeypatch.setattr(cli, '_utcnow', lambda: current_time[0])
        monkeypatch.setattr(action, '_utcnow', lambda: current_time[0])
        inactive = factories.User(name='inactive-member')
        organization = factories.Organization()
        membership = model.Member(
            group_id=organization['id'],
            table_id=inactive['id'],
            table_name='user',
            capacity='editor',
            state=model.State.ACTIVE,
        )
        model.Session.add(membership)
        self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=91),
        )
        original_created = model.User.get(inactive['id']).created

        result = CliRunner().invoke(cli.delete_inactive_users)
        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE

        current_time[0] += timedelta(days=cli.INACTIVITY_WARNING_DAYS_DEFAULT)
        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        assert (
            user_activity.get_inactivity_warning_sent_at(
                model.User.get(inactive['id'])
            ) is None
        )
        action.reactivate_user(
            {'ignore_auth': True},
            {'id': inactive['id']},
        )
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        assert model.User.get(inactive['id']).created == original_created
        retained_membership = model.Session.query(model.Member).filter(
            model.Member.id == membership.id
        ).one()
        assert retained_membership.state == model.State.ACTIVE
        assert retained_membership.capacity == 'editor'

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE

    def test_reactivation_timestamp_keeps_reactivated_user(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        reactivated = factories.User(name='recently-reactivated')
        original_created = self.now - timedelta(days=120)
        old_last_active = self.now - timedelta(days=100)
        user_obj = self._set_user_dates(
            reactivated,
            original_created,
            old_last_active,
        )
        user_activity.set_reactivated_at(user_obj, self.now)
        model.Session.commit()

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        user_obj = model.User.get(reactivated['id'])
        assert user_obj.state == model.State.ACTIVE
        assert user_obj.created == original_created
        assert user_obj.last_active == old_last_active
        assert 'Deleted 0 inactive user(s).' in result.output

    def test_reports_reactivation_as_latest_activity(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        inactive = factories.User(name='old-reactivation')
        user_obj = self._set_user_dates(
            inactive,
            self.now - timedelta(days=180),
            self.now - timedelta(days=100),
        )
        user_activity.set_reactivated_at(
            user_obj,
            self.now - timedelta(days=91),
        )
        model.Session.commit()

        result = CliRunner().invoke(
            cli.delete_inactive_users,
            ['--dry-run'],
        )

        assert result.exit_code == 0, result.output
        assert 'Would send warning email to old-reactivation' in result.output
        assert 'Would delete old-reactivation' not in result.output

    def test_reads_inactivity_days_from_config(self, monkeypatch):
        current_time = [self.now]
        monkeypatch.setattr(cli, '_utcnow', lambda: current_time[0])
        monkeypatch.setitem(
            toolkit.config,
            cli.INACTIVITY_DAYS_CONFIG,
            '30',
        )
        inactive = factories.User(name='configured-cutoff')
        self._set_user_dates(
            inactive,
            self.now - timedelta(days=60),
            self.now - timedelta(days=30, seconds=1),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)
        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE

        current_time[0] += timedelta(days=cli.INACTIVITY_WARNING_DAYS_DEFAULT)
        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED

    @pytest.mark.parametrize('value', [None, 'invalid', '0', '-1'])
    def test_rejects_invalid_inactivity_days_config(
        self,
        monkeypatch,
        value,
    ):
        if value is None:
            monkeypatch.delitem(
                toolkit.config,
                cli.INACTIVITY_DAYS_CONFIG,
                raising=False,
            )
        else:
            monkeypatch.setitem(
                toolkit.config,
                cli.INACTIVITY_DAYS_CONFIG,
                value,
            )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 1
        assert '{} must be a positive integer'.format(
            cli.INACTIVITY_DAYS_CONFIG
        ) in result.output


@pytest.mark.usefixtures('clean_db')
class TestReactivateUserCommand:

    @patch('ckanext.datagov_inventory.notifications.send_unlocked')
    def test_reactivates_deleted_user_by_name(self, send_unlocked):
        deleted_user = factories.User(
            name='deleted-from-cli', state='deleted'
        )

        result = CliRunner().invoke(
            cli.reactivate_user,
            [deleted_user['name']],
        )

        assert result.exit_code == 0, result.output
        assert model.User.get(deleted_user['id']).state == model.State.ACTIVE
        assert 'deleted-from-cli was reactivated' in result.output
        send_unlocked.assert_called_once_with(
            model.User.get(deleted_user['id'])
        )

    def test_rejects_active_user(self):
        active_user = factories.User(name='active-from-cli')

        result = CliRunner().invoke(
            cli.reactivate_user,
            [active_user['name']],
        )

        assert result.exit_code != 0
        assert 'User active-from-cli is not deleted.' in result.output

    def test_reports_unknown_user(self):
        result = CliRunner().invoke(
            cli.reactivate_user,
            ['missing-from-cli'],
        )

        assert result.exit_code != 0
        assert 'User not found: missing-from-cli' in result.output


@pytest.mark.usefixtures('clean_db')
class TestSoftDeleteUserCommand:

    @patch('ckanext.datagov_inventory.notifications.send_locked')
    def test_soft_deletes_active_user_by_name(self, send_locked):
        active_user = factories.User(name='deleted-from-cli')

        result = CliRunner().invoke(
            cli.soft_delete_user,
            [active_user['name']],
        )

        assert result.exit_code == 0, result.output
        assert model.User.get(active_user['id']).state == model.State.DELETED
        assert 'deleted-from-cli was soft-deleted' in result.output
        send_locked.assert_called_once_with(
            model.User.get(active_user['id'])
        )

    def test_rejects_deleted_user(self):
        deleted_user = factories.User(
            name='already-deleted-from-cli', state='deleted'
        )

        result = CliRunner().invoke(
            cli.soft_delete_user,
            [deleted_user['name']],
        )

        assert result.exit_code != 0
        assert (
            'User already-deleted-from-cli is already deleted.'
            in result.output
        )

    def test_reports_unknown_user(self):
        result = CliRunner().invoke(
            cli.soft_delete_user,
            ['missing-from-cli'],
        )

        assert result.exit_code != 0
        assert 'User not found: missing-from-cli' in result.output
