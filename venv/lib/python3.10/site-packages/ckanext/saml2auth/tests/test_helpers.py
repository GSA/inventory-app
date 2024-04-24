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

import pytest

import ckan.authz as authz
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

from ckanext.saml2auth import helpers as h


def test_generate_password():
    password = h.generate_password()
    assert len(password) == 8
    assert type(password) == str


def test_default_login_disabled_by_default():
    assert not h.is_default_login_enabled()


@pytest.mark.ckan_config(u'ckanext.saml2auth.enable_ckan_internal_login', True)
def test_default_login_enabled():
    assert h.is_default_login_enabled()


def test_create_user_via_saml_disabled_by_default():
    assert not h.is_create_user_via_saml_enabled()


@pytest.mark.ckan_config(u'ckanext.saml2auth.create_user_via_saml', True)
def test_create_user_via_saml_enabled():
    assert h.is_create_user_via_saml_enabled()


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckanext.saml2auth.sysadmins_list', '')
def test_00_update_user_sysadmin_status_continue_as_regular():

    user = factories.User(email=u'useroneemail@example.com')
    h.update_user_sysadmin_status(user[u'name'], user[u'email'])
    user_show = helpers.call_action(u'user_show', id=user['id'])
    is_sysadmin = authz.is_sysadmin(user_show[u'name'])

    assert not is_sysadmin


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckanext.saml2auth.sysadmins_list',
                         u'useroneemail@example.com')
def test_01_update_user_sysadmin_status_make_sysadmin():

    user = factories.User(email=u'useroneemail@example.com')
    h.update_user_sysadmin_status(user[u'name'], user[u'email'])
    user_show = helpers.call_action(u'user_show', id=user[u'id'])
    is_sysadmin = authz.is_sysadmin(user_show[u'name'])

    assert is_sysadmin


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckanext.saml2auth.sysadmins_list', 'differentuser@example.com')
def test_02_update_user_sysadmin_status_remove_sysadmin_role():

    user = factories.Sysadmin(email=u'useroneemail@example.com')
    h.update_user_sysadmin_status(user[u'name'], user[u'email'])
    user_show = helpers.call_action(u'user_show', id=user[u'id'])
    is_sysadmin = authz.is_sysadmin(user_show[u'name'])

    assert not is_sysadmin


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckanext.saml2auth.sysadmins_list',
                         u'useroneemail@example.com')
def test_03_update_user_sysadmin_status_continue_as_sysadmin():

    user = factories.Sysadmin(email=u'useroneemail@example.com')
    h.update_user_sysadmin_status(user[u'name'], user[u'email'])
    user_show = helpers.call_action(u'user_show', id=user[u'id'])
    is_sysadmin = authz.is_sysadmin(user_show[u'name'])

    assert is_sysadmin


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
def test_activate_user_if_deleted():
    user = factories.User()
    user = model.User.get(user[u'name'])
    user.delete()
    h.activate_user_if_deleted(user)
    assert not user.is_deleted()


@pytest.mark.usefixtures(u'clean_db')
def test_ensure_unique_user_name_existing_user():

    user = factories.User(
        name='existing-user',
        email=u'existing-user@example.com'
    )

    user_name = h.ensure_unique_username_from_email(user['email'])

    assert user_name != user['email'].split('@')[0]
    assert user_name.startswith(user['email'].split('@')[0])


def test_ensure_unique_user_name_non_existing_user():

    user_name = h.ensure_unique_username_from_email('non-existing-user@example.com')
    assert user_name == 'non-existing-user'
