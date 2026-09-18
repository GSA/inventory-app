"""Tests for user management actions."""

from datetime import datetime, timedelta

import pytest
from pytest import raises as assert_raises

import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckanext.datagov_inventory.plugin import (
    deleted_users_table_section,
    user_org_roles_table_sections,
)

from ckanext.datagov_inventory import action
from ckanext.datagov_inventory import user_activity

is_allowed = True
is_denied = False


def _table_user(name, sysadmin=False, organizations=None):
    return {
        'id': '{}-id'.format(name),
        'name': name,
        'email': '{}@example.com'.format(name),
        'last_active': '',
        'state': 'active',
        'sysadmin': sysadmin,
        'organizations': organizations or [],
    }


def test_user_org_roles_sections_use_one_row_per_user():
    organizations = [
        {'name': 'agency-a', 'title': 'Agency A', 'role': 'admin'},
        {'name': 'agency-b', 'title': 'Agency B', 'role': 'editor'},
    ]
    users = [
        _table_user('sysadmin', sysadmin=True, organizations=organizations),
        _table_user('org-user', organizations=organizations),
    ]

    sections = {
        section['id']: section
        for section in user_org_roles_table_sections(users)
    }

    for section_id in ('sysadmins', 'users-with-organizations'):
        section = sections[section_id]
        assert section['count'] == 1
        assert len(section['rows']) == 1
        assert [item['value'] for item in section['rows'][0][3]['items']] == [
            'agency-a', 'agency-b'
        ]
        assert [item['value'] for item in section['rows'][0][4]['items']] == [
            'admin', 'editor'
        ]


def test_deleted_users_have_their_own_section():
    deleted_user = _table_user('deleted-user')
    deleted_user['state'] = 'deleted'
    users = [_table_user('active-user'), deleted_user]

    sections = user_org_roles_table_sections(users)
    assert [section['id'] for section in sections] == [
        'sysadmins', 'users-with-organizations', 'users-without-organizations'
    ]
    assert sum(section['count'] for section in sections) == 1

    section = deleted_users_table_section(users)
    assert section['count'] == 1
    assert section['rows'][0][0]['value'] == 'deleted-user'
    assert section['columns'] == [
        'user', 'email', 'last_active', 'organization'
    ]
    assert section['sortable'] is True
    assert deleted_users_table_section([])['count'] == 0


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("with_request_context")
@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory')
@pytest.mark.usefixtures('with_plugins')
class TestCreateInventoryUser:

    def setup_method(self):
        self.sysadmin = factories.Sysadmin()
        self.regular_user = factories.User()

    def test_create_user_with_valid_gov_email(self):
        user_dict = {
            'name': 'testuser',
            'email': 'testuser@gsa.gov'
        }

        result = helpers.call_action(
            'create_inventory_user',
            context={'user': self.sysadmin['name']},
            **user_dict
        )

        assert result['name'] == 'testuser'
        assert result['email'] == 'testuser@gsa.gov'
        assert result['state'] == 'active'

    def test_create_user_accepts_any_valid_email(self):
        context = {'user': self.sysadmin['name']}
        user_dict = {
            'name': 'testuser2',
            'email': 'testuser@example.com'
        }

        result = helpers.call_action(
            'create_inventory_user',
            context=context,
            **user_dict
        )

        assert result['name'] == 'testuser2'
        assert result['email'] == 'testuser@example.com'
        assert result['state'] == 'active'

    def test_create_user_handles_duplicate_username(self):
        context = {'user': self.sysadmin['name']}
        user_dict = {
            'name': 'duplicate_user',
            'email': 'user1@gsa.gov'
        }

        helpers.call_action(
            'create_inventory_user',
            context=context,
            **user_dict
        )

        user_dict['email'] = 'user2@gsa.gov'

        with assert_raises(logic.ValidationError) as exc_info:
            helpers.call_action(
                'create_inventory_user',
                context=context,
                **user_dict
            )

        assert 'name' in exc_info.value.error_dict

    def test_create_user_auto_generates_password(self):
        context = {'user': self.sysadmin['name']}
        user_dict = {
            'name': 'testuser3',
            'email': 'testuser3@gsa.gov'
        }

        result = helpers.call_action(
            'create_inventory_user',
            context=context,
            **user_dict
        )

        user_obj = model.User.get(result['id'])
        assert user_obj.password is not None
        assert len(user_obj.password) > 0

    def test_create_user_requires_sysadmin(self):
        context = {
            'user': self.regular_user['name'],
            'ignore_auth': False
        }
        user_dict = {
            'name': 'testuser4',
            'email': 'testuser4@gsa.gov'
        }

        with assert_raises(logic.NotAuthorized):
            helpers.call_action(
                'create_inventory_user',
                context=context,
                **user_dict
            )

    def test_create_user_validates_email_format(self):
        context = {'user': self.sysadmin['name']}
        user_dict = {
            'name': 'testuser5',
            'email': 'invalid-email'
        }

        with assert_raises(logic.ValidationError) as exc_info:
            helpers.call_action(
                'create_inventory_user',
                context=context,
                **user_dict
            )

        assert 'email' in exc_info.value.error_dict


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("with_request_context")
@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory')
@pytest.mark.usefixtures('with_plugins')
class TestReactivateUser:

    def setup_method(self):
        self.sysadmin = factories.Sysadmin()
        self.regular_user = factories.User()

    def test_reactivate_deleted_user(self, monkeypatch):
        deleted_user = factories.User(state='deleted')
        reactivated_at = datetime(2026, 9, 14, 12, 0, 0)
        old_last_active = reactivated_at - timedelta(days=100)
        user_obj = model.User.get(deleted_user['id'])
        original_created = reactivated_at - timedelta(days=120)
        user_obj.created = original_created
        user_obj.last_active = old_last_active
        user_obj.plugin_extras = {'another_extension': {'preserved': True}}
        model.Session.commit()
        monkeypatch.setattr(action, '_utcnow', lambda: reactivated_at)

        context = {'user': self.sysadmin['name']}
        user_dict = {'id': deleted_user['id']}

        result = helpers.call_action(
            'reactivate_user',
            context=context,
            **user_dict
        )

        assert result['state'] == 'active'
        user_obj = model.User.get(deleted_user['id'])
        assert user_obj.state == 'active'
        assert user_obj.created == original_created
        assert user_obj.last_active == old_last_active
        assert user_activity.get_reactivated_at(user_obj) == reactivated_at
        assert user_obj.plugin_extras['another_extension'] == {
            'preserved': True
        }

    def test_reactivate_user_requires_sysadmin(self):
        deleted_user = factories.User(state='deleted')

        context = {
            'user': self.regular_user['name'],
            'ignore_auth': False
        }
        user_dict = {'id': deleted_user['id']}

        with assert_raises(logic.NotAuthorized):
            helpers.call_action(
                'reactivate_user',
                context=context,
                **user_dict
            )

    def test_reactivate_already_active_user(self):
        active_user = factories.User(state='active')

        context = {'user': self.sysadmin['name']}
        user_dict = {'id': active_user['id']}

        with assert_raises(logic.ValidationError) as exc_info:
            helpers.call_action(
                'reactivate_user',
                context=context,
                **user_dict
            )

        assert 'already active' in str(exc_info.value.error_dict).lower()

    def test_reactivate_nonexistent_user(self):
        context = {'user': self.sysadmin['name']}
        user_dict = {'id': 'nonexistent-user-id'}

        with assert_raises(logic.NotFound):
            helpers.call_action(
                'reactivate_user',
                context=context,
                **user_dict
            )

    def test_reactivate_user_by_name(self):
        deleted_user = factories.User(state='deleted')

        context = {'user': self.sysadmin['name']}
        user_dict = {'id': deleted_user['name']}

        result = helpers.call_action(
            'reactivate_user',
            context=context,
            **user_dict
        )

        assert result['state'] == 'active'
        user_obj = model.User.get(deleted_user['name'])
        assert user_obj.state == 'active'


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("with_request_context")
@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory')
@pytest.mark.usefixtures('with_plugins')
class TestSoftDeleteUser:

    def setup_method(self):
        self.sysadmin = factories.Sysadmin()
        self.regular_user = factories.User()

    def test_soft_delete_retains_organization_membership(self):
        user = factories.User()
        organization = factories.Organization()
        membership = model.Member(
            group_id=organization['id'],
            table_id=user['id'],
            table_name='user',
            capacity='editor',
            state=model.State.ACTIVE,
        )
        model.Session.add(membership)
        model.Session.commit()

        result = helpers.call_action(
            'soft_delete_user',
            context={'user': self.sysadmin['name']},
            id=user['id'],
        )

        assert result['state'] == model.State.DELETED
        assert model.User.get(user['id']).state == model.State.DELETED
        retained_membership = model.Session.query(model.Member).filter(
            model.Member.id == membership.id
        ).one()
        assert retained_membership.state == model.State.ACTIVE

    def test_soft_delete_requires_sysadmin(self):
        user = factories.User()

        with assert_raises(logic.NotAuthorized):
            helpers.call_action(
                'soft_delete_user',
                context={'user': self.regular_user['name']},
                id=user['id'],
            )
