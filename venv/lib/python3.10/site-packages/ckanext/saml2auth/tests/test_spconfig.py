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

from ckanext.saml2auth.spconfig import get_config
from ckanext.saml2auth.views.saml2auth import _get_requested_authn_contexts


@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', '/path/to/idp.xml')
def test_read_metadata_local_config():
    assert get_config()[u'metadata'][u'local'] == ['/path/to/idp.xml']


@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'remote')
def test_read_metadata_remote_config():
    with pytest.raises(KeyError):
        assert get_config()[u'metadata'][u'local']

    assert get_config()[u'metadata'][u'remote']


@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'remote')
@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.remote_url', u'https://metadata.com')
@pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.remote_cert', u'/path/to/local.cert')
def test_read_metadata_remote_url():
    with pytest.raises(KeyError):
        assert get_config()[u'metadata'][u'local']

    remote = get_config()[u'metadata'][u'remote'][0]
    assert remote[u'url'] == u'https://metadata.com'
    assert remote[u'cert'] == u'/path/to/local.cert'


@pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
@pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'True')
@pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'True')
def test_signed_settings():

    cfg = get_config()
    assert not cfg[u'service'][u'sp'][u'want_response_signed']
    assert cfg[u'service'][u'sp'][u'want_assertions_signed']
    assert cfg[u'service'][u'sp'][u'want_assertions_or_response_signed']


@pytest.mark.ckan_config(u'ckanext.saml2auth.key_file_path', u'/path/to/mykey.pem')
@pytest.mark.ckan_config(u'ckanext.saml2auth.cert_file_path', u'/path/to/mycert.pem')
@pytest.mark.ckan_config(u'ckanext.saml2auth.attribute_map_dir', u'/path/to/attribute_map_dir')
def test_paths():

    cfg = get_config()
    assert cfg[u'key_file'] == u'/path/to/mykey.pem'
    assert cfg[u'cert_file'] == u'/path/to/mycert.pem'
    assert cfg[u'encryption_keypairs'] == [{u'key_file': '/path/to/mykey.pem', u'cert_file': '/path/to/mycert.pem'}]
    assert cfg[u'attribute_map_dir'] == '/path/to/attribute_map_dir'


def test_name_id_policy_format_default_not_set():
    assert 'name_id_policy_format' not in get_config()[u'service'][u'sp']


@pytest.mark.ckan_config(u'ckanext.saml2auth.sp.name_id_policy_format', 'some_policy_format')
def test_name_id_policy_format_set_in_config():

    name_id_policy_format = get_config()[u'service'][u'sp'][u'name_id_policy_format']
    assert name_id_policy_format == 'some_policy_format'


@pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'some:entity_id')
def test_read_entity_id():

    entity_id = get_config()[u'entityid']
    assert entity_id == u'some:entity_id'


@pytest.mark.ckan_config(u'ckanext.saml2auth.acs_endpoint', u'/my/acs/endpoint')
def test_read_acs_endpoint():

    acs_endpoint = get_config()[u'service'][u'sp'][u'endpoints'][u'assertion_consumer_service'][0]
    assert acs_endpoint.endswith('/my/acs/endpoint')


@pytest.mark.ckan_config(u'ckanext.saml2auth.requested_authn_context', u'req1')
def test_one_requested_authn_context():

    contexts = _get_requested_authn_contexts()
    assert contexts[0] == u'req1'


@pytest.mark.ckan_config(u'ckanext.saml2auth.requested_authn_context', u'req1 req2')
def test_two_requested_authn_context():

    contexts = _get_requested_authn_contexts()
    assert u'req1' in contexts
    assert u'req2' in contexts


@pytest.mark.ckan_config(u'ckanext.saml2auth.requested_authn_context', None)
def test_empty_requested_authn_context():

    contexts = _get_requested_authn_contexts()
    assert contexts == []
