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

from saml2.saml import NAME_FORMAT_URI
from saml2 import entity

from ckan.common import config as ckan_config
from ckan.common import asbool, aslist


def get_config():
    """ Get the config
        Read: https://pysaml2.readthedocs.io/en/latest/howto/config.html
        """

    base = ckan_config.get('ckan.site_url')
    debug = asbool(ckan_config.get('debug'))
    allow_unknown_attributes = \
        ckan_config.get(u'ckanext.saml2auth.allow_unknown_attributes', True)
    name_id_format = \
        aslist(ckan_config.get(u'ckanext.saml2auth.sp.name_id_format',
                               "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"))
    name_id_policy_format = ckan_config.get(u'ckanext.saml2auth.sp.name_id_policy_format')

    location = \
        ckan_config.get(u'ckanext.saml2auth.idp_metadata.location')
    local_path = \
        ckan_config.get(u'ckanext.saml2auth.idp_metadata.local_path')
    remote_url = \
        ckan_config.get(u'ckanext.saml2auth.idp_metadata.remote_url')
    # Consider different name
    remote_cert = \
        ckan_config.get(u'ckanext.saml2auth.idp_metadata.remote_cert')

    entity_id = ckan_config.get(u'ckanext.saml2auth.entity_id', u'urn:mace:umu.se:saml:ckan:sp')
    response_signed = asbool(ckan_config.get(u'ckanext.saml2auth.want_response_signed', True))
    assertion_signed = asbool(ckan_config.get(u'ckanext.saml2auth.want_assertions_signed', False))
    any_signed = asbool(ckan_config.get(u'ckanext.saml2auth.want_assertions_or_response_signed', False))
    key_file = ckan_config.get(u'ckanext.saml2auth.key_file_path', None)
    cert_file = ckan_config.get(u'ckanext.saml2auth.cert_file_path', None)
    attribute_map_dir = ckan_config.get(u'ckanext.saml2auth.attribute_map_dir', None)
    acs_endpoint = ckan_config.get('ckanext.saml2auth.acs_endpoint', '/acs')
    logout_requests_signed = \
        asbool(ckan_config.get(u'ckanext.saml2auth.logout_requests_signed', False))
    logout_expected_binding = ckan_config.get(u'ckanext.saml2auth.logout_expected_binding',
                                              entity.BINDING_HTTP_POST)

    config = {
        u'entityid': entity_id,
        u'description': u'CKAN saml2 Service Provider',
        # Set True if eg.Azure or Microsoft Idp used
        u'allow_unknown_attributes': allow_unknown_attributes,
        u'service': {
            u'sp': {
                u'name': u'CKAN SP',
                u'endpoints': {
                    u'assertion_consumer_service': [base + acs_endpoint]
                },
                u'allow_unsolicited': True,
                u'name_id_format': name_id_format,
                u'want_response_signed': response_signed,
                u'want_assertions_signed': assertion_signed,
                u'want_assertions_or_response_signed': any_signed,
                u'logout_requests_signed': logout_requests_signed
            }
        },
        u'logout_expected_binding': logout_expected_binding,
        u'metadata': {},
        u'debug': 1 if debug else 0,
        u'name_form': NAME_FORMAT_URI
        }

    if name_id_policy_format:
        config[u'service'][u'sp'][u'name_id_policy_format'] = name_id_policy_format

    if key_file is not None and cert_file is not None:
        config[u'key_file'] = key_file
        config[u'cert_file'] = cert_file
        config[u'encryption_keypairs'] = [{u'key_file': key_file, u'cert_file': cert_file}]

    if attribute_map_dir is not None:
        config[u'attribute_map_dir'] = attribute_map_dir

    if location == u'local':
        config[u'metadata'][u'local'] = [local_path]
    elif location == u'remote':
        remote = [{
                u'url': remote_url,
                u'cert': remote_cert
            }]
        config[u'metadata'][u'remote'] = remote

    return config
