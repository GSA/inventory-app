"""Tests for datagov_inventory plugin.py."""

from pytest import raises as assert_raises
import pytest

import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.tests.helpers import FunctionalTestBase

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.datastore.tests.helpers as datastore_helpers

from ckanext.datagov_inventory.plugin import inventory_package_show

import logging

log = logging.getLogger(__name__)

# Define allowed/denied values
is_allowed = True
is_denied = False


@pytest.mark.usefixtures(u"clean_index")
@pytest.mark.usefixtures(u"clean_db")
@pytest.mark.usefixtures("with_request_context")
class TestDatagovInventoryAuth(FunctionalTestBase):

    def setup(self):
        super(TestDatagovInventoryAuth, self).setup_class()
        # Start with a clean database and index for each test
        self.clean_datastore()

    # @pytest.fixture()
    # def app(make_app):
    #     from flask.sessions import SecureCookieSessionInterface
    #     app = make_app()
    #     app.flask_app.session_interface = SecureCookieSessionInterface()
    #     return app

    def create_datasets(self):
        self.sysadmin = factories.Sysadmin(name='admin')
        self.user = factories.User()
        self.organization = factories.Organization()
        self.extra_environ = {'REMOTE_USER': self.sysadmin['name']}
        self.extra_environ_user = {'REMOTE_USER': self.user['name']}

        self.dataset1 = {
            'name': 'my_package_000',
            'title': 'my package',
            'notes': 'my package notes',
            'public_access_level': 'public',
            'access_level_comment': 'Access level comment',
            'unique_id': '000',
            'contact_name': 'Jhon',
            'program_code': '018:001',
            'bureau_code': '019:20',
            'contact_email': 'jhon@mail.com',
            'publisher': 'Publicher 01',
            'modified': '2019-01-27 11:41:21',
            'tag_string': 'mypackage,tag01,tag02',
            'private': 'true',
            'owner_org': self.organization['id']
        }

        for key in self.sysadmin:
            if key not in ['id', 'name']:
                self.dataset1.update({key: self.sysadmin[key]})
        self.dataset_private = factories.Dataset(**self.dataset1)

        self.dataset2 = self.dataset1.copy()
        self.dataset2['name'] = 'my_package_111'
        self.dataset2['unique_id'] = '111'
        self.dataset2['private'] = 'false'
        self.dataset_public = factories.Dataset(**self.dataset2)

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

        # Create doi organization and add users
        org_users = [{'name': 'doi_admin', 'capacity': 'admin'},
                     {'name': 'doi_member', 'capacity': 'member'}]
        factories.Organization(users=org_users, name='doi')

    # def login_users(self):
    #     for user in self.test_users:
    #         print(self.test_users[user]['id'])
    #         user_model = model.User.get(self.test_users[user]['id'])
    #         try:
    #             toolkit.login_user(user_model, False, 5000, False, False)
    #         except BaseException as err:
    #             print(err)

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
        return ({'package_id': dataset['id'],
                 'tag_id': dataset_params['tag_string'],
                 'resource_id': dataset['resources'][0]['id']})
        # 'revision_id': dataset['revision_id']})

    def assert_user_authorization(self,
                                  auth_function,
                                  expected_user_access_dict,
                                  object_id=None):

        for user in expected_user_access_dict:
            # anonymous users need to pass user context as ''
            user_context = self.test_users[user]['name'] if self.test_users[user] else ''
            context = {
                'model': model,
                'ignore_auth': False,
                'user': user_context}

            if expected_user_access_dict[user]:
                # We expect users to have access, validate
                actual_authorization = helpers.call_auth(auth_function,
                                                         context=context,
                                                         id=object_id)
                assert actual_authorization == expected_user_access_dict[user]
            else:
                # We expect users to be denied
                print(context)
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
            'anonymous': is_denied
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

    def test_auth_user_list(self):
        '''
        IMPORTANT CHANGE: This test allowed all users access to the 'user_list'
        function until CKAN 2.10.  We don't know why the functionality
        changed.  But only sysadmin can access this function in tests.
        From the UI, it seems like all users have access to this operation.
        '''
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('user_list', {
            'gsa_admin': is_denied,
            'gsa_editor': is_denied,
            'gsa_member': is_denied,
            'doi_admin': is_denied,
            'doi_member': is_denied,
            'anonymous': is_denied
        })

    def test_auth_user_show(self):
        '''
        IMPORTANT CHANGE: This test allowed all users access to the 'user_show'
        function until CKAN 2.10.  We don't know why the functionality
        changed.  But only sysadmin can access this function in tests.
        From the UI, it seems like all users have access to this operation.
        '''
        # Create test users and test data
        self.setup_test_orgs_users()

        self.assert_user_authorization('user_show', {
            'gsa_admin': is_denied,
            'gsa_editor': is_denied,
            'gsa_member': is_denied,
            'doi_admin': is_denied,
            'doi_member': is_denied,
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

    def test_resource_show_request_public_dataset(self):
        self.app = self._get_test_app()

        self.create_datasets()
        context = {'user': None, 'model': model}
        data_dict = {'id': self.dataset_public['id']}
        test_url = '/dataset/'+'0'*36+'/resource/'+'0'*36+'/download/1'
        with self.app.flask_app.test_request_context(test_url):
            assert inventory_package_show(context,
                                          data_dict) == {'success': True}

    def test_resource_show_request_private_dataset(self):
        self.app = self._get_test_app()

        self.create_datasets()
        context = {'user': None, 'model': model}
        data_dict = {'id': self.dataset_private['id']}
        test_url = '/dataset/'+'0'*36+'/resource/'+'0'*36+'/download/1'
        with self.app.flask_app.test_request_context(test_url):
            assert inventory_package_show(context,
                                          data_dict) == {'success': False}
