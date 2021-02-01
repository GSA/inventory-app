"""Tests for datagov_inventory plugin.py."""

from nose.tools import assert_raises
from nose.tools import assert_equal

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.logic as logic

import logging

log = logging.getLogger(__name__)


class TestDatagovInventoryAuth(object):

    @classmethod
    def setup_class(self):
        '''Nose runs this method once to setup our test class.'''

        # Start with a clean database
        model.repo.rebuild_db()

        # Create test user that is editor of test organization    

        self.test_users = {
            'gsa_admin' : factories.User(name='gsa_admin'),
            'gsa_editor' : factories.User(name='gsa_editor'),
            'gsa_member' : factories.User(name='gsa_member'),
            'doi_member' : factories.User(name='doi_member'),
            'anonymous' : ''
        }

        # Create gsa organization and add users
        org_users = [{'name': 'gsa_admin', 'capacity': 'admin'},
                     {'name': 'gsa_editor', 'capacity': 'editor'},
                     {'name': 'gsa_member', 'capacity': 'member'}]
        org_dict = factories.Organization(users=org_users,
                                          name='gsa')

        # Create gsa organization and add users
        org_users = [{'name': 'doi_member', 'capacity': 'member'}]
        org_dict = factories.Organization(users=org_users,
                                          name='doi')


    def setup(self):
        '''Nose runs this method before each test method in our test class.'''

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''

    def _setup_private_gsa_dataset(self):

        private_dataset_params = {
            'private': 'true',
            'name': 'private_test_package',
            'title': 'private test package',
            'tag_string': 'test_package',
            'modified': '2014-04-04',
            'publisher': 'GSA',
            'contact_name': 'john doe',
            'contact_email': 'john.doe@gsa.com',
            'unique_id': '002',
            'public_access_level': 'non-public',
            'bureau_code': '001:40',
            'program_code': '015:010',
            'license_id': 'http://creativecommons.org/publicdomain/zero/1.0/',
            'license_new': 'http://creativecommons.org/publicdomain/zero/1.0/',
            'owner_org': 'gsa',
            'resources': [
                {
                    'name': 'private_resource',
                    'id': 'private_resource_id',
                    'url': 'www.google.com',
                    'description': 'description'}
            ]
        }

        # Create public package/dataset
        return (factories.Dataset(**private_dataset_params))


    def assert_user_authorization(self, auth_function, context, expected_user_access_dict):
        # Assert the expected_user_access_dict is complete for our matrix of access roles.
        #  It's an error if the test case is missing an expectation.
        assert 'gsa_admin' in expected_user_access_dict
        assert 'gsa_editor' in expected_user_access_dict
        assert 'gsa_member' in expected_user_access_dict
        assert 'doi_member' in expected_user_access_dict
        assert 'anonymous' in expected_user_access_dict

        for user in expected_user_access_dict:
            context['user'] = user  # apply the user to the given context
            actual_authorization = helpers.call_auth(auth_function, context=context) # assert NotAuthorized and return a boolean value for assertion
            assert actual_authorization == expected_user_access_dict[user]

    def test_auth_resource_show_for_private_gsa_dataset(self):
        is_allowed = True
        is_denied = False

        private_gsa_dataset = self._setup_private_gsa_dataset()
        context = {
            'model': model,
            'ignore_auth': False,
            'user': '',
            'id' : 'private_resource_id'
        }
        self.assert_user_authorization('resource_show', context, {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_allowed
    })

    
