"""Tests for Inventory user profile details."""

from datetime import datetime

import pytest

import ckan.model as model
import ckan.tests.factories as factories
from ckan.lib.helpers import url_for

from ckanext.datagov_inventory import user_activity


@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory')
@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestUserProfile:
    def _get_profile(self, app, user):
        response = app.get(
            url_for('user.read', id=user['name']),
            extra_environ={'REMOTE_USER': user['name']},
            status=200,
        )
        return response.data.decode('utf-8')

    def test_displays_reactivated_at_after_member_since(self, app):
        user = factories.User()
        user_obj = model.User.get(user['id'])
        user_activity.set_reactivated_at(
            user_obj,
            datetime(2026, 9, 14, 12, 0, 0),
        )
        model.Session.commit()

        profile = self._get_profile(app, user)

        assert profile.index('Member Since') < profile.index('Reactivated At')

    def test_omits_reactivated_at_when_unavailable(self, app):
        user = factories.User()

        profile = self._get_profile(app, user)

        assert 'Reactivated At' not in profile

    def test_sysadmin_can_delete_active_user_from_profile(self, app):
        user = factories.User()
        admin = factories.Sysadmin()

        response = app.get(
            url_for('user.read', id=user['name']),
            extra_environ={'REMOTE_USER': admin['name']},
            status=200,
        )

        profile = response.data.decode('utf-8')
        assert 'Delete user' in profile
        assert 'soft-delete/{}'.format(user['id']) in profile

    def test_sysadmin_can_reactivate_deleted_user_from_profile(self, app):
        user = factories.User(state='deleted')
        admin = factories.Sysadmin()

        response = app.get(
            url_for('user.read', id=user['name']),
            extra_environ={'REMOTE_USER': admin['name']},
            status=200,
        )

        profile = response.data.decode('utf-8')
        assert 'Reactivate user' in profile
        assert 'reactivate/{}'.format(user['id']) in profile
