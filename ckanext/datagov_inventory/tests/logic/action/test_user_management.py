"""Tests for user management actions."""

import pytest
from pytest import raises as assert_raises

import ckan.logic as logic
import ckan.model as model
from ckan.tests.helpers import FunctionalTestBase
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

is_allowed = True
is_denied = False


@pytest.mark.usefixtures("clean_db")
@pytest.mark.usefixtures("with_request_context")
class TestCreateInventoryUser(FunctionalTestBase):

    def setup_method(self):
        super(TestCreateInventoryUser, self).setup_class()
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

    def test_create_user_rejects_non_gov_email(self):
        context = {'user': self.sysadmin['name']
        }
        user_dict = {
            'name': 'testuser2',
            'email': 'testuser@gmail.com'
        }

        with assert_raises(logic.ValidationError) as exc_info:
            helpers.call_action(
                'create_inventory_user',
                context=context,
                **user_dict
            )

        assert 'email' in exc_info.value.error_dict
        assert '.gov' in str(exc_info.value.error_dict['email'])

    def test_create_user_handles_duplicate_username(self):
        context = {'user': self.sysadmin['name']
        }
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
        context = {'user': self.sysadmin['name']
        }
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
        context = {'user': self.sysadmin['name']
        }
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
