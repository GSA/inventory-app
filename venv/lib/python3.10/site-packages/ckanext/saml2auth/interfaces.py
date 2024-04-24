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

from ckan.plugins.interfaces import Interface


class ISaml2Auth(Interface):
    u'''
    This interface allows plugins to hook into the Saml2 authorization flow
    '''
    def before_saml2_user_update(self, user_dict, saml_attributes):
        u'''
        Called just before updating an existing user

        :param user_dict: User metadata dict that will be passed to user_update
        :param saml_attributes: A dict containing extra SAML attributes returned
            as part of the SAML Response
        '''
        pass

    def before_saml2_user_create(self, user_dict, saml_attributes):
        u'''
        Called just before creating a new user

        :param user_dict: User metadata dict that will be passed to user_create
        :param saml_attributes: A dict containing extra SAML attributes returned
            as part of the SAML Response
        '''
        pass

    def after_saml2_login(self, resp, saml_attributes):
        u'''
        Called once the user has been logged in programatically, just before
        returning the request. The logged in user can be accessed using g.user
        or g.userobj

        It should always return the provided response object (which can be of course
        modified)

        :param resp: A Flask response object. Can be used to issue
            redirects, add headers, etc
        :param saml_attributes: A dict containing extra SAML attributes returned
            as part of the SAML Response
        '''
        return resp
