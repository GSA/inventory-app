# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc.
 Author: Pierre-Yves Chibon <pingou@pingoured.fr>

 Distributed under License GPLv3 or later
 You can find a copy of this license on the website
 http://www.gnu.org/licenses/gpl.html

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 MA 02110-1301, USA.
"""

import os
import sys

from flask import Flask
from flask.helpers import send_from_directory
from werkzeug.exceptions import NotFound


PY2 = sys.version_info[0] == 2
if PY2:
    string_types = (str, unicode)
else:
    string_types = (str,)


class MultiStaticFlask(Flask):
    ''' This class inherit from the main Flask application object and
    override few methods to allow flask to support having multiple folders
    serving static content.
    '''

    def _get_static_folder(self):
        if self._static_folder is not None:
            return [os.path.join(self.root_path, folder)
                    for folder in self._static_folder]
    def _set_static_folder(self, value):
        folders = value
        if isinstance(folders, string_types):
            folders = [value]
        self._static_folder = folders
    static_folder = property(_get_static_folder, _set_static_folder)
    del _get_static_folder, _set_static_folder

    # Use the last entry in the list of static folder as it should be what
    # contains most of the files
    def _get_static_url_path(self):
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return '/' + os.path.basename(self.static_folder[-1])
    def _set_static_url_path(self, value):
        self._static_url_path = value
    static_url_path = property(_get_static_url_path, _set_static_url_path)
    del _get_static_url_path, _set_static_url_path


    def send_static_file(self, filename):
        """Function used internally to send static files from the static
        folder to the browser.

        .. versionadded:: 0.5
        """
        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')

        # Ensure get_send_file_max_age is called in all cases.
        # Here, we ensure get_send_file_max_age is called for Blueprints.
        cache_timeout = self.get_send_file_max_age(filename)

        folders = self.static_folder
        if isinstance(self.static_folder, string_types):
            folders = [self.static_folder]

        for directory in folders:
            try:
                return send_from_directory(
                    directory, filename, cache_timeout=cache_timeout)
            except NotFound:
                pass
        raise NotFound()
