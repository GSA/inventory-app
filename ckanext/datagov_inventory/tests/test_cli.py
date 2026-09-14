"""Tests for Inventory CKAN commands."""

from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

import ckan.model as model
import ckan.tests.factories as factories

from ckanext.datagov_inventory import cli


@pytest.mark.usefixtures('clean_db')
class TestDeleteInactiveUsers:
    now = datetime(2026, 9, 11, 12, 0, 0)

    def _set_user_dates(self, user, created, last_active):
        user_obj = model.User.get(user['id'])
        user_obj.created = created
        user_obj.last_active = last_active
        model.Session.commit()
        return user_obj

    def test_deletes_users_with_old_last_active(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        inactive = factories.User(name='inactive')
        boundary = factories.User(name='boundary')
        recent = factories.User(name='recent')

        self._set_user_dates(
            inactive,
            self.now,
            self.now - timedelta(days=90, seconds=1),
        )
        self._set_user_dates(
            boundary,
            self.now,
            self.now - timedelta(days=90),
        )
        self._set_user_dates(
            recent,
            self.now,
            self.now - timedelta(days=89),
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        assert model.User.get(boundary['id']).state == model.State.ACTIVE
        assert model.User.get(recent['id']).state == model.State.ACTIVE
        assert 'Deleted 1 inactive user(s).' in result.output

    def test_uses_creation_date_when_last_active_is_null(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        inactive = factories.User(name='never-active-old')
        recent = factories.User(name='never-active-recent')

        self._set_user_dates(
            inactive,
            self.now - timedelta(days=90, seconds=1),
            None,
        )
        self._set_user_dates(
            recent,
            self.now - timedelta(days=89),
            None,
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        assert model.User.get(recent['id']).state == model.State.ACTIVE
        assert 'Deleting never-active-old (created:' in result.output

    def test_dry_run_does_not_delete_users(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        inactive = factories.User(name='inactive-dry-run')
        self._set_user_dates(
            inactive,
            self.now,
            self.now - timedelta(days=91),
        )

        result = CliRunner().invoke(
            cli.delete_inactive_users,
            ['--dry-run'],
        )

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        assert 'Would delete inactive-dry-run (last_active:' in result.output
        assert 'Would delete 1 inactive user(s).' in result.output
