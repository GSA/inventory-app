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
import logging
from saml2.client import Saml2Client

from ckanext.saml2auth.spconfig import get_config as sp_config

log = logging.getLogger(__name__)


class Saml2Client(Saml2Client):

    def do_logout(self, *args, **kwargs):
        if not kwargs.get('expected_binding'):
            try:
                kwargs['expected_binding'] = sp_config()[u'logout_expected_binding']
            except AttributeError:
                log.warning('ckanext.saml2auth.logout_expected_binding'
                            'is not defined. Default binding will be used.')
        return super().do_logout(*args, **kwargs)
