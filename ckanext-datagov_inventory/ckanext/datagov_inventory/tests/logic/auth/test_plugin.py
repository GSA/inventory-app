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
                        'private': 'false',
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
                        'private': 'true',
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

        # Create public package/dataset
        public_dataset = factories.Dataset(**public_dataset_params)
        self.public_dataset_id = public_dataset.get("id")
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

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''


    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''

        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        # model.repo.rebuild_db()
    
    def _anon_rejected_auth_test(self, auth_function):
        context = {
            'model': model,
            'ignore_auth': False,
            'user': 'org_editor_test_user'
        }
        # Test user access
        assert_equal(helpers.call_auth(auth_function,context=context), True)

        context['user'] = None
        # Test anonymous user is refused
        assert_raises(logic.NotAuthorized, helpers.call_auth, auth_function,context=context)

    def test_format_autocomplete(self):
        '''Test format_autocomplete expected output'''
        log.debug("Running test_format_autocomplete")
        self._anon_rejected_auth_test('format_autocomplete')

    def test_org_user_access_to_public_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_public_package_show")

        context = {
            'model': model,
            'ignore_auth': False,
            'user': 'org_editor_test_user'
        }

        assert_equal(helpers.call_auth('package_show',context=context, id=self.public_dataset_id), True)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_non_org_user_access_to_public_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to__public_package_show")
        
        context = {
            'model': model,
            'ignore_auth': False,
            'user': 'non_org_test_user'
        }
        assert_equal(helpers.call_auth('package_show', context=context, id=self.public_dataset_id), True)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_anon_user_access_to_public_package_show(self):
        '''Test anonymous access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_public_package_show")

        context = {
            'model': model,
            'ignore_auth': False,
            'user': None
        }
        assert_equal(helpers.call_auth('package_show', context=context, id=self.public_dataset_id), True)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.public_resource_id), True)

    def test_org_user_access_to_private_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_org_user_access_to_private_package_show")

        # Put the mock model in the context.
        context = {
            'model': model,
            'ignore_auth': False,
            'user': 'org_editor_test_user'
        }
        assert_equal(helpers.call_auth('package_show', context=context, id=self.private_dataset_id), True)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)

    def test_non_org_user_access_to_private_package_show(self):
        '''Test logged in organization editor access to package_show and resource_show'''

        log.debug("Running test_non_org_user_access_to_private_package_show")

        context = {
            'model': model,
            'ignore_auth': False,
            'user': 'non_org_test_user'
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.private_dataset_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)

    def test_anon_user_access_to_private_package_show(self):
        '''Test anonymous access to package_show and resource_show'''

        log.debug("Running test_anon_user_access_to_public_private_show")

        context = {
            'model': model,
            'ignore_auth': False,
            'user': None
        }
        assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', context=context, id=self.private_dataset_id)
        assert_equal(helpers.call_auth('resource_show',context=context, id=self.private_resource_id), True)
