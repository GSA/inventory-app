# encoding: utf-8

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
import pytest

from ckan.plugins import toolkit
from ckan.plugins.toolkit import url_for

here = os.path.dirname(os.path.abspath(__file__))
extras_folder = os.path.join(here, 'extras')


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'saml2auth')
class TestBlueprint(object):

    def test_user_register_disabled_by_default(self, app):
        url = url_for(u'user.register')
        response = app.get(url=url)
        assert 403 == response.status_code

        assert u'This resource is forbidden' \
               u' by the system administrator. ' \
               u'Only SSO through SAML2 authorization ' \
               u'is available at this moment.' in response

    def test_internal_user_login_disabled_by_deafult(self, app):
        url = url_for(u'user.login')
        response = app.get(url=url)
        assert 403 == response.status_code

        assert u'This resource is forbidden' \
               u' by the system administrator. ' \
               u'Only SSO through SAML2 authorization ' \
               u'is available at this moment.' in response

    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path',
                             os.path.join(extras_folder, 'provider2', 'idp.xml'))
    def test_came_from_sent_as_relay_state(self, app):

        url = url_for('saml2auth.saml2login', came_from='/dataset/my-dataset')

        response = app.get(url=url, follow_redirects=False)
        assert 'RelayState=%2Fdataset%2Fmy-dataset' in response.headers['Location']

    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path',
                             os.path.join(extras_folder, 'provider2', 'idp.xml'))
    @pytest.mark.usefixtures('with_request_context')
    def test_cookies_cleared_on_slo(self, app):
        if toolkit.check_ckan_version(min_version='2.10'):
            # Remove when dropping support for 2.9
            pytest.skip("auth_tkt cookie has been deprecated in 2.10")
        url = url_for('user.logout')

        import datetime
        from unittest import mock
        from http.cookies import SimpleCookie
        from flask import make_response
        from dateutil.parser import parse as date_parse

        with mock.patch(
            'ckanext.saml2auth.plugin._perform_slo',
                return_value=make_response('')):
            response = app.get(url=url, follow_redirects=False)

        cookie_headers = [
            h[1] for h in response.headers
            if h[0].lower() == 'set-cookie']

        assert len(cookie_headers) == 2

        for cookie_header in cookie_headers:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            cookie_name = [name for name in cookie.keys()][0]
            assert cookie_name in ['auth_tkt', 'ckan']
            assert cookie[cookie_name]['domain'] == 'test.ckan.net'
            cookie_date = date_parse(cookie[cookie_name]['expires'], ignoretz=True)
            assert cookie_date < datetime.datetime.now()

    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path',
                             os.path.join(extras_folder, 'provider2', 'idp.xml'))
    @pytest.mark.usefixtures('with_request_context')
    def test_ckan_cookie_cleared_on_slo(self, app):
        if not toolkit.check_ckan_version(min_version='2.10'):
            # Remove when dropping support for 2.9
            pytest.skip("This test logic introduced in CKAN 2.10")
        url = url_for('user.logout')

        import datetime
        from unittest import mock
        from http.cookies import SimpleCookie
        from flask import make_response
        from dateutil.parser import parse as date_parse

        with mock.patch(
            'ckanext.saml2auth.plugin._perform_slo',
                return_value=make_response('')):
            response = app.get(url=url, follow_redirects=False)

        cookie_headers = [
            h[1] for h in response.headers
            if h[0].lower() == 'set-cookie']

        # Starting 2.10, CKAN's SessionMiddleware will append a
        # new Set-cookie header on every first response from the server.
        # This includes test requests.
        assert len(cookie_headers) == 2

        first_cookie = cookie_headers[0]

        cookie = SimpleCookie()
        cookie.load(first_cookie)
        cookie_name = [name for name in cookie.keys()][0]
        assert cookie_name == 'ckan'
        assert cookie[cookie_name]['domain'] == 'test.ckan.net'
        cookie_date = date_parse(cookie[cookie_name]['expires'], ignoretz=True)
        assert cookie_date < datetime.datetime.now()
