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

import base64
from datetime import datetime
from jinja2 import Template
import os
import pytest
try:
    from unittest import mock
except ImportError:
    import mock

from ckan import model
from ckan.plugins import toolkit

from saml2.xmldsig import SIG_RSA_SHA256
from saml2.xmldsig import DIGEST_SHA256
from saml2.saml import NAMEID_FORMAT_ENTITY
from saml2.saml import Issuer
from saml2.server import Server
from saml2.authn_context import INTERNETPROTOCOLPASSWORD


here = os.path.dirname(os.path.abspath(__file__))
extras_folder = os.path.join(here, 'extras')
responses_folder = os.path.join(here, 'responses')


def _b4_encode_string(message):
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    return base64_bytes.decode('ascii')


def _prepare_unsigned_response():
    # read about saml2 responses: https://www.samltool.com/generic_sso_res.php
    unsigned_response_file = os.path.join(responses_folder, 'unsigned0.xml')
    unsigned_response = open(unsigned_response_file).read()
    # parse values
    context = {
        'entity_id': 'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity',
        'destination': 'http://test.ckan.net/acs',
        'recipient': 'http://test.ckan.net/acs',
        'issue_instant': datetime.now().isoformat()
    }
    t = Template(unsigned_response)
    final_response = t.render(**context)

    encoded_response = _b4_encode_string(final_response)

    return encoded_response


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'saml2auth')
class TestGetRequest:
    """ test getting request from external source """

    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_empty_request(self, app):

        url = '/acs'
        data = {
            'SAMLResponse': ''
        }
        response = app.post(url=url, status=400, params=data)
        assert 400 == response.status_code
        assert u'Empty login request' in response

    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_bad_request(self, app):

        url = '/acs'
        data = {
            'SAMLResponse': '<saml>'
        }
        response = app.post(url=url, status=400, params=data)
        assert 400 == response.status_code
        assert u'Bad login request' in response

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_unsigned_request(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }
        response = app.post(url=url, params=data)
        assert 200 == response.status_code

    def render_file(self, path, context, save_as=None):
        """ open file and render contect values """
        txt = open(path).read()
        t = Template(txt)
        response = t.render(**context)

        if save_as is not None:
            f = open(save_as, 'w')
            f.write(response)
            f.close()

        return response

    def _load_base(
        self,
        destination='http://test.ckan.net/acs',
        issuer_url='https://organization.com/saml/',
        entity_id='urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity'
    ):

        cert_file = os.path.join(extras_folder, 'provider1', 'mycert.pem')
        f = open(cert_file)
        cert = f.read()
        f.close()

        x509_cert = cert.replace('\x0D', '')
        x509_cert = x509_cert.replace('\r', '')
        x509_cert = x509_cert.replace('\n', '')
        x509_cert = x509_cert.replace('-----BEGIN CERTIFICATE-----', '')
        x509_cert = x509_cert.replace('-----END CERTIFICATE-----', '')
        x509_cert = x509_cert.replace(' ', '')

        self.context = {
            'entity_id': entity_id,
            'entity_session_id': '_session_ID_44444',
            'issuer_url': issuer_url,
            'destination': destination,
            'org_name': 'IDP Organization',
            'org_url': 'https://idp.organization.com',
            'redirect_login_url': 'https://idp.organization.com/auth',
            'attributes_url': 'https://idp.organization.com/attributes',
            'certificate': x509_cert
        }

        self.render_file(
            path=os.path.join(extras_folder, 'provider1', 'idp_cert_template.xml'),
            context=self.context,
            save_as=os.path.join(extras_folder, 'provider1', 'idp.xml')
        )

        key_file = os.path.join(extras_folder, 'provider1', 'mykey.pem')
        cert_file = os.path.join(extras_folder, 'provider1', 'mycert.pem')
        self.config = {
            'description': 'CKAN saml2 Service Provider',
            'service': {
                'sp': {
                    'name_id_format': [
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:persistent',
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress'
                    ],
                    'want_response_signed': False,
                    'name': 'CKAN SP',
                    'want_assertions_signed': True,
                    'allow_unsolicited': True,
                    'endpoints': {
                        'assertion_consumer_service': ['http://ckan:5000/acs', 'http://test.ckan.net/acs']
                    },
                    'want_assertions_or_response_signed': True,
                    'name_id_policy_format': [
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:persistent',
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
                        'urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress'
                    ]
                }
            },
            'name_form': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
            'debug': 0,
            'entityid': entity_id,
            'allow_unknown_attributes': 'true',
            'metadata': {
                'local': [os.path.join(extras_folder, 'provider1', 'idp.xml')]
            },
            'key_file': key_file,
            'cert_file': cert_file,
            'encryption_keypairs': [
                {'key_file': key_file, 'cert_file': cert_file}
            ]
        }

    def _generate_cert(self):
        from saml2.cert import OpenSSLWrapper

        cert_info_ca = {
            "cn": "localhost.ca",
            "country_code": "se",
            "state": "ac",
            "city": "umea",
            "organization": "Test University",
            "organization_unit": "Deca"
        }

        osw = OpenSSLWrapper()
        ca_cert, ca_key = osw.create_certificate(
            cert_info_ca,
            request=False,
            write_to_file=False
        )

        cert_str, key_str = osw.create_certificate(cert_info_ca, request=True)
        re_cert_str = osw.create_cert_signed_certificate(
            ca_cert,
            ca_key,
            cert_str,
            valid_from=0,
            valid_to=1
        )

        f = open(os.path.join(extras_folder, 'provider1', 'mycert.pem'), 'w')
        f.write(re_cert_str)
        f.close()

        f = open(os.path.join(extras_folder, 'provider1', 'mykey.pem'), 'wb')
        f.write(key_str)
        f.close()

        self.key_str = key_str
        self.cert_str = re_cert_str

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider1', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'True')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.key_file_path', os.path.join(extras_folder, 'provider1', 'mykey.pem'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.cert_file_path', os.path.join(extras_folder, 'provider1', 'mycert.pem'))
    def test_encrypted_assertion(self, app):

        self._generate_cert()
        self._load_base()

        # define the user identity
        IDENTITY = {
            "eduPersonAffiliation": ["staff", "member"],
            "surName": ["Jeter"], "givenName": ["Derek"],
            "email": ["foo@gmail.com"],
            "title": ["shortstop"]
        }

        # start a server to generate the expected response
        server = Server(self.config)
        name_id = server.ident.transient_nameid(self.context['entity_id'], "id12")
        issuer = Issuer(text=self.context['entity_id'], format=NAMEID_FORMAT_ENTITY)
        authn = {
            "class_ref": INTERNETPROTOCOLPASSWORD,
            "authn_auth": "http://www.example.com/login"
        }
        response = server.create_authn_response(
            identity=IDENTITY,
            in_response_to="id12",
            destination=self.context['destination'],
            sp_entity_id=self.context['entity_id'],
            name_id=name_id,
            sign_assertion=True,
            sign_response=True,
            issuer=issuer,
            sign_alg=SIG_RSA_SHA256,
            digest_alg=DIGEST_SHA256,
            encrypt_assertion=True,
            encrypt_cert_assertion=self.cert_str,
            encrypt_assertion_self_contained=True,
            authn=authn
        )

        # finishe the response and b64 encode to send to our /acs endpoint
        final_signed_response = response  # .to_string()

        # To check the response
        f = open(os.path.join(extras_folder, 'provider1', 'test-signed-encrypted.xml'), 'w')
        f.write(final_signed_response)
        f.close()
        encoded_response = _b4_encode_string(final_signed_response)
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }
        response = app.post(url=url, params=data)
        assert 200 == response.status_code

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider1', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'True')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.key_file_path', os.path.join(extras_folder, 'provider1', 'mykey.pem'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.cert_file_path', os.path.join(extras_folder, 'provider1', 'mycert.pem'))
    def test_signed_not_encrypted_assertion(self, app):

        self._generate_cert()
        self._load_base()

        # define the user identity
        IDENTITY = {
            "eduPersonAffiliation": ["staff", "member"],
            "surName": ["Jeter"], "givenName": ["Derek"],
            "email": ["foo@gmail.com"],
            "title": ["shortstop"]
        }

        # start a server to generate the expected response
        server = Server(self.config)
        name_id = server.ident.transient_nameid(self.context['entity_id'], "id12")
        issuer = Issuer(text=self.context['entity_id'], format=NAMEID_FORMAT_ENTITY)
        authn = {
            "class_ref": INTERNETPROTOCOLPASSWORD,
            "authn_auth": "http://www.example.com/login"
        }
        response = server.create_authn_response(
            identity=IDENTITY,
            in_response_to="id12",
            destination=self.context['destination'],
            sp_entity_id=self.context['entity_id'],
            name_id=name_id,
            sign_assertion=True,
            sign_response=True,
            issuer=issuer,
            sign_alg=SIG_RSA_SHA256,
            digest_alg=DIGEST_SHA256,
            authn=authn
        )

        # finishe the response and b64 encode to send to our /acs endpoint
        final_signed_response = response  # .to_string()

        # To check the response
        f = open(os.path.join(extras_folder, 'provider1', 'test-signed.xml'), 'w')
        f.write(final_signed_response)
        f.close()
        encoded_response = _b4_encode_string(final_signed_response)
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }
        response = app.post(url=url, params=data)
        assert 200 == response.status_code

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_user_fullname_using_first_last_name(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }
        response = app.post(url=url, params=data)
        assert 200 == response.status_code

        user = model.User.by_email('test@example.com')
        if isinstance(user, list):
            user = user[0]

        assert user.fullname == 'John Smith'

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.user_fullname', u'fullname')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.user_firstname', None)
    @pytest.mark.ckan_config(u'ckanext.saml2auth.user_lastname', None)
    def test_user_fullname_using_fullname(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }
        response = app.post(url=url, params=data)
        assert 200 == response.status_code

        user = model.User.by_email('test@example.com')
        if isinstance(user, list):
            user = user[0]

        assert user.fullname == 'John Smith (Operations)'

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_relay_state_redirects_to_local_page(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response,
            'RelayState': '/dataset/my-dataset'
        }
        response = app.post(url=url, params=data, follow_redirects=False)

        assert response.headers['Location'] == 'http://test.ckan.net/dataset/my-dataset'

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_no_relay_state_redirects_to_fallback_default(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response,
        }
        response = app.post(url=url, params=data, follow_redirects=False)

        assert response.headers['Location'] == 'http://test.ckan.net/user/me'

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.default_fallback_endpoint', 'dataset.search')
    def test_no_relay_state_redirects_to_fallback_config(self, app):

        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response,
        }
        response = app.post(url=url, params=data, follow_redirects=False)

        assert response.headers['Location'] == 'http://test.ckan.net/dataset/'

    @pytest.mark.ckan_config(u'ckanext.saml2auth.entity_id', u'urn:gov:gsa:SAML:2.0.profiles:sp:sso:test:entity')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.location', u'local')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.idp_metadata.local_path', os.path.join(extras_folder, 'provider0', 'idp.xml'))
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_response_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_signed', u'False')
    @pytest.mark.ckan_config(u'ckanext.saml2auth.want_assertions_or_response_signed', u'False')
    def test_repoze_user_id(self, app):
        if not toolkit.check_ckan_version(max_version='2.9.6'):
            # Remove when dropping support for 2.9.6
            pytest.skip("set_repoze_user has been deprecated in 2.10")
        encoded_response = _prepare_unsigned_response()
        url = '/acs'

        data = {
            'SAMLResponse': encoded_response
        }

        with mock.patch("ckanext.saml2auth.views.saml2auth.set_repoze_user") as m:
            app.post(url=url, params=data)

            user = model.User.by_email('test@example.com')
            if isinstance(user, list):
                user = user[0]

            assert m.called
            # Check login worked fine by checking the Response object
            assert m.call_args[0][1].headers["Location"].endswith("/user/me")

            if toolkit.check_ckan_version(min_version="2.9.6"):
                assert m.call_args[0][0] == user.id + ",1"
            else:
                assert m.call_args[0][0] == user.name
