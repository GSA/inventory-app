"""Tests for Inventory CKAN commands."""

from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

import ckan.model as model
import ckan.plugins.toolkit as toolkit
import ckan.tests.factories as factories

from ckanext.datagov_inventory import action, cli


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
            self.now - timedelta(days=180),
            self.now - timedelta(days=90, seconds=1),
        )
        self._set_user_dates(
            boundary,
            self.now - timedelta(days=180),
            self.now - timedelta(days=90),
        )
        self._set_user_dates(
            recent,
            self.now - timedelta(days=180),
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
            self.now - timedelta(days=180),
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

    def test_soft_delete_retains_organization_membership(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        monkeypatch.setattr(action, '_utcnow', lambda: self.now)
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

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        assert model.User.get(inactive['id']).state == model.State.DELETED
        action.reactivate_user(
            {'ignore_auth': True},
            {'id': inactive['id']},
        )
        assert model.User.get(inactive['id']).state == model.State.ACTIVE
        retained_membership = model.Session.query(model.Member).filter(
            model.Member.id == membership.id
        ).one()
        assert retained_membership.state == model.State.ACTIVE
        assert retained_membership.capacity == 'editor'

    def test_new_creation_date_keeps_reactivated_user(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
        reactivated = factories.User(name='recently-reactivated')
        old_last_active = self.now - timedelta(days=100)
        self._set_user_dates(
            reactivated,
            self.now,
            old_last_active,
        )

        result = CliRunner().invoke(cli.delete_inactive_users)

        assert result.exit_code == 0, result.output
        user_obj = model.User.get(reactivated['id'])
        assert user_obj.state == model.State.ACTIVE
        assert user_obj.last_active == old_last_active
        assert 'Deleted 0 inactive user(s).' in result.output

    def test_reads_inactivity_days_from_config(self, monkeypatch):
        monkeypatch.setattr(cli, '_utcnow', lambda: self.now)
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
