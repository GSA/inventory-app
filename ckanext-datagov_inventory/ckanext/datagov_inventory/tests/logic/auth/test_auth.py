"""Tests for datagov_inventory plugin.py."""

from nose.tools import assert_raises

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.logic as logic

import ckanext.datastore.tests.helpers as test_helpers

import logging

log = logging.getLogger(__name__)


class TestDatagovInventoryAuth(object):

    @classmethod
    def setup_class(self):
        '''Nose runs this method once to setup our test class.'''

        # Start with a clean database
        model.repo.rebuild_db()

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''

        # Start with a clean database for each test
        self._clean_datastore
        model.repo.rebuild_db()


    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''

    def _setup_test_orgs_users(self):

        # Create test users 
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
        gsa_org_dict = factories.Organization(users=org_users,
                                          name='gsa')

        # Create gsa organization and add users
        org_users = [{'name': 'doi_member', 'capacity': 'member'}]
        doi_org_dict = factories.Organization(users=org_users,
                                          name='doi')

    def _clean_datastore(self):
        engine = test_helpers.db.get_write_engine()
        test_helpers.rebuild_all_dbs(
            test_helpers.orm.scoped_session(
                test_helpers.orm.sessionmaker(bind=engine)
            )
        )

    def _setup_private_gsa_dataset(self):

        private_dataset_params = {
            'private': 'true',
            'name': 'private_test_package',
            'title': 'private test package',
            'id': 'private_package_id',
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
        dataset = factories.Dataset(**private_dataset_params)
        log.debug('Private Dataset Id %s', dataset['id'])
        # Return id string for the package and resoruce just created
        return({'package_id' : 'private_package_id', 'resource_id': 'private_resource_id'})

    def _setup_public_gsa_dataset(self):

        private_dataset_params = {
            'private': 'true',
            'name': 'public_test_package',
            'title': 'public test package',
            'id' : 'public_package_id',
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
                    'name': 'public_resource',
                    'id': 'public_resource_id',
                    'url': 'www.google.com',
                    'description': 'description'}
            ]
        }
        factories.Dataset(**public_dataset_params)
        # Return id string for the package and resoruce just created
        return({'package_id' : 'public_package_id', 'resource_id': 'public_resource_id'})


    def assert_user_authorization(self, auth_function, object_id, expected_user_access_dict):
        # Assert the expected_user_access_dict is complete for our matrix of access roles.
        #  It's an error if the test case is missing an expectation.
        assert 'gsa_admin' in expected_user_access_dict
        assert 'gsa_editor' in expected_user_access_dict
        assert 'gsa_member' in expected_user_access_dict
        assert 'doi_member' in expected_user_access_dict
        assert 'anonymous' in expected_user_access_dict

        for user in expected_user_access_dict:
            context = {
                'model': model,
                'ignore_auth': False,
                'user': user}
            log.debug('For Loop Context: %s', context)
            if expected_user_access_dict[user]:
                actual_authorization = helpers.call_auth(auth_function, context=context, id=object_id)
                assert actual_authorization == expected_user_access_dict[user]
            else:
                assert_raises(logic.NotAuthorized, helpers.call_auth, auth_function, context=context, id=object_id)

    def test_auth_resource_show_for_private_gsa_dataset(self):
        is_allowed = True
        is_denied = False
        
        # Create test users and test data
        self._setup_test_orgs_users()
        dataset = self._setup_private_gsa_dataset()

        self.assert_user_authorization('resource_show', dataset['resource_id'], {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_allowed
        })

    def test_auth_package_show_for_private_gsa_dataset(self):
        is_allowed = True
        is_denied = False

        # Create test users and test data
        self._setup_test_orgs_users()
        dataset = self._setup_private_gsa_dataset()
    
        log.debug('Test package_show Package Id %s', dataset)
        self.assert_user_authorization('package_show', dataset['package_id'], {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_member': is_denied,
            'anonymous': is_denied
        })