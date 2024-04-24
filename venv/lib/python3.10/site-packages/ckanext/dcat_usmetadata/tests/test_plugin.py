"""Tests for plugin.py."""

import ckan.plugins

import ckan.tests.factories as factories
from ckan.tests import helpers
import ckanext.dcat_usmetadata.cli as cli
from click.testing import CliRunner

import json
import os
import pytest


@pytest.mark.usefixtures('with_request_context')
class TestDcatUsmetadataPlugin(helpers.FunctionalTestBase):
    '''
        Tests for the ckanext.dcat_usmetadata.plugin module.
        The main tests are written in cypress for nodejs/
        reactjs UI elements.
    '''

    @classmethod
    def setup(cls):
        helpers.reset_db()

    @classmethod
    def setup_class(cls):
        super(TestDcatUsmetadataPlugin, cls).setup_class()

    def create_user(self):
        self.sysadmin = factories.Sysadmin(name='admin')
        self.organization = factories.Organization(name='test-organization')
        self.extra_environ = {'REMOTE_USER': self.sysadmin['name']}

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
            'parent_dataset': 'true',
            'owner_org': self.organization['id']
        }

        for key in self.sysadmin:
            if key not in ['id', 'name']:
                self.dataset1.update({key: self.sysadmin[key]})
        self.dataset1 = factories.Dataset(**self.dataset1)

    def test_plugin_loaded(self):
        assert ckan.plugins.plugin_loaded('dcat_usmetadata')

    def test_package_creation(self):
        '''
        test if dataset is getting created successfully
        '''
        self.create_user()
        self.app = self._get_test_app()
        package_dict = self.app.get('/api/3/action/package_show?id=my_package_000',
                                    extra_environ=self.extra_environ)

        result = json.loads(package_dict.body)['result']
        assert result['name'] == 'my_package_000'

    def test_publisher_load(self):
        self.create_user()
        runner = CliRunner()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        result = runner.invoke(cli.import_publishers, [dir_path + "/../publishers.test.csv"])
        self.app = self._get_test_app()
        org = self.app.get('/api/action/organization_show?id=%s' % (self.organization['id']),
                           extra_environ=self.extra_environ)
        assert json.loads(org.body)['result']['name'] == 'test-organization'

        assert result.exit_code == 0
        assert "Updated publishers" in result.output
