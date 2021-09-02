"""Tests for datagov_inventory plugin.py."""

from builtins import object
from pytest import raises as assert_raises
import pytest

import ckan.logic as logic
import ckan.model as model

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.datastore.tests.helpers as datastore_helpers

import logging

log = logging.getLogger(__name__)

# Define allowed/denied values
is_allowed = True
is_denied = False


@pytest.mark.usefixtures(u"clean_index")
@pytest.mark.usefixtures(u"clean_db")
class TestDatagovInventoryAuth(object):

    def setup(self):
        # Start with a clean database and index for each test
        self.clean_datastore()

    def setup_test_orgs_users(self):

        # Create test users
        self.test_users = {
            'gsa_admin': factories.User(name='gsa_admin'),
            'gsa_editor': factories.User(name='gsa_editor'),
            'gsa_member': factories.User(name='gsa_member'),
            'doi_admin': factories.User(name='doi_admin'),
            'doi_member': factories.User(name='doi_member'),
            'anonymous': ''
        }

        # Create gsa organization and add users
        org_users = [{'name': 'gsa_admin', 'capacity': 'admin'},
                     {'name': 'gsa_editor', 'capacity': 'editor'},
                     {'name': 'gsa_member', 'capacity': 'member'}]
        factories.Organization(users=org_users, name='gsa')

        # Create gsa organization and add users
        org_users = [{'name': 'doi_admin', 'capacity': 'admin'},
                     {'name': 'doi_member', 'capacity': 'member'}]
        factories.Organization(users=org_users, name='doi')

    def clean_datastore(self):
        engine = datastore_helpers.db.get_write_engine()
        datastore_helpers.rebuild_all_dbs(
            datastore_helpers.orm.scoped_session(
                datastore_helpers.orm.sessionmaker(bind=engine)
            )
        )

    def factory_dataset(self, **kwargs):
        # Defaults
        dataset_params = {
            'private': False,
            'title': 'Test package',
            'tag_string': 'test_tag',
            'modified': '2014-04-04',
            'publisher': 'GSA',
            'contact_name': 'john doe',
            'contact_email': 'john.doe@gsa.com',
            'unique_id': '001',
            'public_access_level': 'public',
            'bureau_code': '001:40',
            'program_code': '015:010',
            'license_id': 'http://creativecommons.org/publicdomain/zero/1.0/',
            'owner_org': 'gsa',
            'resources': [
                {
                    'name': 'test_resource',
                    'url': 'www.example.com',
                    'description': 'description'}
            ]
        }

        # Overwrite the defaults as specified
        dataset_params.update(kwargs)
        dataset = factories.Dataset(**dataset_params)
        # Return id string for the package and resoruce just created
        return({'package_id': dataset['id'],
                'tag_id': dataset_params['tag_string'],
                'resource_id': dataset['resources'][0]['id']})
        # 'revision_id': dataset['revision_id']})

    def assert_user_authorization(self,
                                  auth_function,
                                  expected_user_access_dict,
                                  object_id=None):
        # Assert the expected_user_access_dict is complete for our matrix of
        #  access roles. It's an error if the test case is missing an
        #  expectation.
        assert 'gsa_admin' in expected_user_access_dict
        assert 'gsa_editor' in expected_user_access_dict
        assert 'gsa_member' in expected_user_access_dict
        assert 'doi_admin' in expected_user_access_dict
        assert 'doi_member' in expected_user_access_dict
        assert 'anonymous' in expected_user_access_dict

        for user in expected_user_access_dict:
            context = {
                'model': model,
                'ignore_auth': False,
                'user': user}
            if expected_user_access_dict[user]:
                # We expect users to have access, validate
                actual_authorization = helpers.call_auth(auth_function,
                                                         context=context,
                                                         id=object_id)
                assert actual_authorization == expected_user_access_dict[user]
            else:
                # We expect users to be denied
                with assert_raises(logic.NotAuthorized):
                    helpers.call_auth(auth_function,
                                      context=context,
                                      id=object_id)

    def test_auth_format_autocomplete(self):
        # Create test users and test group
        self.setup_test_orgs_users()

        self.assert_user_authorization('format_autocomplete', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_group_list(self):
        # Create test users and test group
        self.setup_test_orgs_users()

        self.assert_user_authorization('group_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_license_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        self.factory_dataset()

        self.assert_user_authorization('license_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_member_roles_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('member_roles_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_organization_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('organization_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_package_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        self.factory_dataset(owner_org='gsa', private=False)

        self.assert_user_authorization('package_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_package_search(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        self.factory_dataset(owner_org='gsa', private=True)
        self.factory_dataset(owner_org='gsa', private=False)

        self.assert_user_authorization('package_search', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_package_show_for_private_gsa_dataset(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        datasest = self.factory_dataset(owner_org='gsa', private=True)

        self.assert_user_authorization('package_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_denied,
            'doi_member': is_denied,
            'anonymous': is_denied
        }, object_id=datasest['package_id'])

    def test_auth_package_show_for_public_gsa_dataset(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        dataset = self.factory_dataset(owner_org='gsa', private=False)

        self.assert_user_authorization('package_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_allowed
        }, object_id=dataset['package_id'])

    def test_auth_resource_show_for_private_gsa_dataset(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        dataset = self.factory_dataset(owner_org='gsa', private=True)

        self.assert_user_authorization('resource_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_denied,
            'doi_member': is_denied,
            'anonymous': is_denied
        }, object_id=dataset['resource_id'])

    def test_auth_resource_show_for_public_gsa_dataset(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        dataset = self.factory_dataset(owner_org='gsa', private=False)

        self.assert_user_authorization('resource_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_allowed
        }, object_id=dataset['resource_id'])

    def test_auth_site_read(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('site_read', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_tag_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        self.factory_dataset(owner_org='gsa', private=True)

        self.assert_user_authorization('tag_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_tag_show(self):
        # Create test users and test data
        self.setup_test_orgs_users()
        dataset = self.factory_dataset(owner_org='gsa', private=True)

        self.assert_user_authorization('tag_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        }, dataset['tag_id'])

    def test_auth_task_status_show(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('task_status_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_vocabulary_list(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('vocabulary_list', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })

    def test_auth_vocabulary_show(self):
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('vocabulary_show', {
            'gsa_admin': is_allowed,
            'gsa_editor': is_allowed,
            'gsa_member': is_allowed,
            'doi_admin': is_allowed,
            'doi_member': is_allowed,
            'anonymous': is_denied
        })
