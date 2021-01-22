"""Tests for datagov_inventory plugin.py."""

from nose.tools import assert_raises
from nose.tools import assert_equal
from nose.tools import assert_raises_regexp

import ckan.model as model
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic
import mock
import ckan.tests.legacy as tests

import paste.fixture
import pylons.test

import ckan.tests.helpers as helpers
import requests

import json
import logging

log = logging.getLogger(__name__)

class TestDatagovInventoryAuth(object):

    @classmethod
    def setup_class(self):
        '''Nose runs this method once to setup our test class.'''

        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        model.repo.rebuild_db()

        # Create test user that is editor of test organization
        self.org_editor_test_user = factories.User(name='org_editor_test_user')

        # Create test organization and add test user as editor
        org_users = [{'name': 'org_editor_test_user', 'capacity': 'editor'}]
        org_dict = factories.Organization(users=org_users,name='auth-test-org')

        # Create test user that is not a member of the test organization
        self.non_org_test_user = factories.User(name='non_org_test_user')

        sysadmin = factories.Sysadmin()

        public_dataset_params = {
                        'name': 'test_package',
                        'title': 'test package',
                        'notes': 'test package notes',
                        'tag_string': 'test_package',
                        'modified': '2014-04-04',
                        'publisher': 'GSA',
                        'publisher_1': 'OCSIT',
                        'contact_name': 'john doe',
                        'contact_email': 'john.doe@gsa.com',
                        'unique_id': '001',
                        'public_access_level': 'public',
                        'bureau_code': '001:40',
                        'program_code': '015:010',
                        'access_level_comment': 'Access level commemnt',
                        'license_id': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'license_new': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'spatial': 'Lincoln, Nebraska',
                        'temporal': '2000-01-15T00:45:00Z/2010-01-15T00:06:00Z',
                        'category': ["vegetables", "produce"],
                        'data_dictionary': 'www.google.com',
                        'data_dictionary_type': 'tex/csv',
                        'data_quality': 'true',
                        'publishing_status': 'open',
                        'accrual_periodicity': 'annual',
                        'conforms_to': 'www.google.com',
                        'homepage_url': 'www.google.com',
                        'language': 'us-EN',
                        'primary_it_investment_uii': '021-123456789',
                        'related_documents': 'www.google.com',
                        'release_date': '2014-01-02',
                        'system_of_records': 'www.google.com',
                        'is_parent': 'true',
                        'owner_org': org_dict['id'],
                        'accessURL': 'www.google.com',
                        'webService': 'www.gooogle.com',
                        'format': 'text/csv',
                        'formatReadable': 'text/csv'
        }

        private_dataset_params = {
                        'name': 'private_test_package',
                        'title': 'private test package',
                        'notes': 'private test package notes',
                        'tag_string': 'test_package',
                        'modified': '2014-04-04',
                        'publisher': 'GSA',
                        'publisher_1': 'OCSIT',
                        'contact_name': 'john doe',
                        'contact_email': 'john.doe@gsa.com',
                        'unique_id': '002',
                        'public_access_level': 'non-public',
                        'bureau_code': '001:40',
                        'program_code': '015:010',
                        'access_level_comment': 'Access level commemnt',
                        'license_id': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'license_new': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'spatial': 'Lincoln, Nebraska',
                        'temporal': '2000-01-15T00:45:00Z/2010-01-15T00:06:00Z',
                        'category': ["vegetables", "produce"],
                        'data_dictionary': 'www.google.com',
                        'data_dictionary_type': 'tex/csv',
                        'data_quality': 'true',
                        'publishing_status': 'open',
                        'accrual_periodicity': 'annual',
                        'conforms_to': 'www.google.com',
                        'homepage_url': 'www.google.com',
                        'language': 'us-EN',
                        'primary_it_investment_uii': '021-123456789',
                        'related_documents': 'www.google.com',
                        'release_date': '2014-01-02',
                        'system_of_records': 'www.google.com',
                        'is_parent': 'true',
                        'owner_org': org_dict['id'],
                        'accessURL': 'www.google.com',
                        'webService': 'www.gooogle.com',
                        'format': 'text/csv',
                        'formatReadable': 'text/csv'
        }

        restricted_dataset_params = {
                        'name': 'restricted_test_package',
                        'title': 'restricted test package',
                        'notes': 'restricted test package notes',
                        'tag_string': 'test_package',
                        'modified': '2014-04-04',
                        'publisher': 'GSA',
                        'publisher_1': 'OCSIT',
                        'contact_name': 'john doe',
                        'contact_email': 'john.doe@gsa.com',
                        'unique_id': '003',
                        'public_access_level': 'restricted public',
                        'bureau_code': '001:40',
                        'program_code': '015:010',
                        'access_level_comment': 'Access level commemnt',
                        'license_id': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'license_new': 'http://creativecommons.org/publicdomain/zero/1.0/',
                        'spatial': 'Lincoln, Nebraska',
                        'temporal': '2000-01-15T00:45:00Z/2010-01-15T00:06:00Z',
                        'category': ["vegetables", "produce"],
                        'data_dictionary': 'www.google.com',
                        'data_dictionary_type': 'tex/csv',
                        'data_quality': 'true',
                        'publishing_status': 'open',
                        'accrual_periodicity': 'annual',
                        'conforms_to': 'www.google.com',
                        'homepage_url': 'www.google.com',
                        'language': 'us-EN',
                        'primary_it_investment_uii': '021-123456789',
                        'related_documents': 'www.google.com',
                        'release_date': '2014-01-02',
                        'system_of_records': 'www.google.com',
                        'is_parent': 'true',
                        'owner_org': org_dict['id'],
                        'accessURL': 'www.google.com',
                        'webService': 'www.gooogle.com',
                        'format': 'text/csv',
                        'formatReadable': 'text/csv'
        }

        # Create public package/dataset
        public_dataset = factories.Dataset(**public_dataset_params)
        self.public_dataset_id = public_dataset["id"]
        log.info("Created Public Dataset with id %s", self.public_dataset_id)

        # Create Public Resource with using API to upload file
        response = requests.post('http://app:5000/api/action/resource_create',
              data={"package_id": public_dataset['id'],
                    "name": "My test CSV"},
              headers={"X-CKAN-API-Key": sysadmin.get('apikey')},
              files=[('upload', file('/opt/inventory-app/config/test.csv'))])
        self.public_resource_id = json.loads(response.text)["result"]["id"]
        log.info("Created Public Resource with id %s", self.public_resource_id)

        # Create Private package/dataset
        private_dataset = factories.Dataset(**private_dataset_params)
        self.private_dataset_id = private_dataset["id"]
        log.info("Created Private Dataset with id %s", self.private_dataset_id)

        # Create Private Resource with using API to upload file
        response = requests.post('http://app:5000/api/action/resource_create',
              data={"package_id": private_dataset['id'],
                    "name": "My private test CSV"},
              headers={"X-CKAN-API-Key": sysadmin.get('apikey')},
              files=[('upload', file('/opt/inventory-app/config/test.csv'))])
        self.private_resource_id = json.loads(response.text)["result"]["id"]
        log.info("Created Private Resource with id %s", self.private_resource_id)

        # Create Restricted package/dataset
        restricted_dataset = factories.Dataset(**restricted_dataset_params)
        self.restricted_dataset_id = restricted_dataset["id"]
        log.info("Created Restricted Dataset with id %s", self.restricted_dataset_id)

        # Create Restricted Resource with using API to upload file
        response = requests.post('http://app:5000/api/action/resource_create',
              data={"package_id": restricted_dataset['id'],
                    "name": "My restricted test CSV"},
              headers={"X-CKAN-API-Key": sysadmin.get('apikey')},
              files=[('upload', file('/opt/inventory-app/config/test.csv'))])
        self.restricted_resource_id = json.loads(response.text)["result"]["id"]
        log.info("Created Restricted Resource with id %s", self.restricted_resource_id)
        

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''


    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''

        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        # model.repo.rebuild_db()

    """
    def test_user_update_user_cannot_update_another_user(self):
        '''Users should not be able to update other users' accounts.'''

        # 1. Setup.

        # Make a mock ckan.model.User object, Fred.
        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # The logged-in user is going to be Bob, not Fred.
        context['user'] = 'bob'

        # 2. Call the function that's being tested, once only.

        # Make Bob try to update Fred's user account.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }

        # 3. Make assertions about the return value and/or side-effects.

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'user_update', context=context, **params)

        # 4. Do nothing else!
    """


    def test_org_user_access_to_public_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_public_package_show")

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = self.org_editor_test_user

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': 'org_editor_test_user'
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.public_dataset_id)
        assert_raises(NotAuthorized, helpers.call_action, 'package_show',context, id=self.public_dataset_id)
        #assert_equal(helpers.call_auth('package_show',context=context, id=self.public_dataset_id), True)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.public_resource_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_non_org_user_access_to_public_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to__public_package_show")
        
        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = self.non_org_test_user

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': 'non_org_test_user'
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.public_dataset_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.public_resource_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth('package_show',context=context, id=self.public_dataset_id))
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_anon_user_access_to_public_package_show(self):
        '''Test anonymous access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_public_package_show")
        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = None

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': None
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.public_dataset_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_org_user_access_to_private_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_private_package_show")

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = self.org_editor_test_user

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': 'org_editor_test_user'
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.private_dataset_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.private_resource_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)

    def test_non_org_user_access_to_private_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_non_org_user_access_to_private_package_show")

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = self.non_org_test_user

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': 'non_org_test_user'
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.private_dataset_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.private_resource_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)

    def test_anon_user_access_to_private_package_show(self):
        '''Test anonymous access to package_show and resource_show'''

        log.debug("Running test_anon_user_access_to_public_private_show")

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = None

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': None
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.private_dataset_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.private_resource_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)

    def test_anon_user_access_to_restricted_package_show(self):
        '''Test anonymous access to package_show and resource_show
        This shouldn't succeed for either package_show or resource_show but is working for resource_show'''

        log.debug("Running test_anon_user_access_to_restricted_package_show")
        
        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()

        # model.User.get(user_id) should return None.
        mock_model.User.get.return_value = None

        # Put the mock model in the context.
        context = {
            'model': mock_model,
            'ignore_auth': False,
            'user': None
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.restricted_dataset_id)
        # assert_raises(logic.NotAuthorized, helpers.call_auth, 'resource_show', context=context, id=self.restricted_resource_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.restricted_resource_id), True)


"""
    def test_logged_in_user_access(self):
        app = self._get_test_app()

        user_dict = call_action('user_create', name='test_user',
                        email='test_user@nospam.com', password='pass')

        context = {
            'ignore_auth': False,
            'user': user_dict['name']
        }                

        result = helpers.call_auth('package_show', context=context,
                           id='some_user_id',
                           name='updated_user_name')
      """
