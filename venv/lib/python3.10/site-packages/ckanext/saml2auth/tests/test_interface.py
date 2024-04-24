"""
Copyright (c) 2020 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
from collections import defaultdict

import pytest

import ckan.model as model
import ckan.plugins as plugins
from ckan.tests import factories

from ckanext.saml2auth.interfaces import ISaml2Auth
from ckanext.saml2auth.tests.test_blueprint_get_request import (
    _prepare_unsigned_response
)

here = os.path.dirname(os.path.abspath(__file__))
extras_folder = os.path.join(here, 'extras')


class ExampleISaml2AuthPlugin(plugins.SingletonPlugin):

    plugins.implements(ISaml2Auth, inherit=True)

    def __init__(self, *args, **kwargs):

        self.calls = defaultdict(int)

    def before_saml2_user_update(self, user_dict, saml_attributes):

        self.calls['before_saml2_user_update'] += 1

        user_dict['fullname'] += ' TEST UPDATE'

        user_dict['plugin_extras']['my_plugin'] = {}
        user_dict['plugin_extras']['my_plugin']['key1'] = 'value1'

    def before_saml2_user_create(self, user_dict, saml_attributes):

        self.calls['before_saml2_user_create'] += 1

        user_dict['fullname'] += ' TEST CREATE'

        user_dict['plugin_extras']['my_plugin'] = {}
        user_dict['plugin_extras']['my_plugin']['key2'] = 'value2'

    def after_saml2_login(self, resp, saml_attributes):

        self.calls['after_saml2_login'] += 1

        resp.headers['X-Custom-header'] = 'test'

        return resp


@pytest.mark.usefixtures(u'clean_db', u'with_plugins')
@pytest.mark.ckan_config(u'ckan.plugins', u'saml2auth')
@pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
@pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
@pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
@pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
class TestInterface(object):

    def test_after_login_is_called(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }

        with plugins.use_plugin("test_saml2auth") as plugin:
            response = app.post(url=url, params=data, follow_redirects=False)
            assert 302 == response.status_code

            assert plugin.calls["after_saml2_login"] == 1, plugin.calls

            assert response.headers['X-Custom-header'] == 'test'

    def test_before_create_is_called(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }

        with plugins.use_plugin("test_saml2auth") as plugin:
            response = app.post(url=url, params=data, follow_redirects=False)
            assert 302 == response.status_code

            assert plugin.calls["before_saml2_user_create"] == 1, plugin.calls

        user = model.User.by_email('test@example.com')
        if isinstance(user, list):
            user = user[0]

        assert user.fullname.endswith('TEST CREATE')

        assert user.plugin_extras['my_plugin']['key2'] == 'value2'

        assert 'saml_id' in user.plugin_extras['saml2auth']

    def test_before_update_is_called_on_saml_user(self, app):

        # From unsigned0.xml
        saml_id = '_ce3d2948b4cf20146dee0a0b3dd6f69b6cf86f62d7'

        user = factories.User(
            email='test@example.com',
            plugin_extras={
                'saml2auth': {
                    'saml_id': saml_id,
                }
            }
        )

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }

        with plugins.use_plugin("test_saml2auth") as plugin:
            response = app.post(url=url, params=data, follow_redirects=False)
            assert 302 == response.status_code

            assert plugin.calls["before_saml2_user_update"] == 1, plugin.calls

        user = model.User.by_email('test@example.com')
        if isinstance(user, list):
            user = user[0]

        assert user.fullname.endswith('TEST UPDATE')

        assert user.plugin_extras['my_plugin']['key1'] == 'value1'

        assert user.plugin_extras['saml2auth']['saml_id'] == saml_id

    def test_before_update_is_called_on_ckan_user(self, app):

        user = factories.User(
            email='test@example.com',
        )

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }

        with plugins.use_plugin("test_saml2auth") as plugin:
            response = app.post(url=url, params=data, follow_redirects=False)
            assert 302 == response.status_code

            assert plugin.calls["before_saml2_user_update"] == 1, plugin.calls

        user = model.User.by_email('test@example.com')
        if isinstance(user, list):
            user = user[0]

        assert user.fullname.endswith('TEST UPDATE')

        assert 'saml_id' in user.plugin_extras['saml2auth']
