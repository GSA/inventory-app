from sqlalchemy.util import OrderedDict

import logging

from ckan.plugins.toolkit import config
from ckan import plugins as p
from ckan.lib import helpers as h
import re
import simplejson as json

REDACTED_REGEX = re.compile(
    r'^(\[\[REDACTED).*?(\]\])$'
)

REDACTED_TAGS_REGEX = re.compile(
    r'\[\[/?REDACTED(-EX\sB\d)?\]\]'
)

PARTIAL_REDACTION_REGEX = re.compile(
    r'\[\[REDACTED-EX B[\d]\]\](.*?\[\[/REDACTED\]\])'
)

log = logging.getLogger(__name__)


def get_reference_date(date_str):
    """
        Gets a reference date extra created by the harvesters and formats it
        nicely for the UI.

        Examples:
            [{"type": "creation", "value": "1977"}, {"type": "revision", "value": "1981-05-15"}]
            [{"type": "publication", "value": "1977"}]
            [{"type": "publication", "value": "NaN-NaN-NaN"}]

        Results
            1977 (creation), May 15, 1981 (revision)
            1977 (publication)
            NaN-NaN-NaN (publication)
    """
    try:
        out = []
        for date in h.json.loads(date_str):
            value = h.render_datetime(date['value']) or date['value']
            out.append('{0} ({1})'.format(value, date['type']))
        return ', '.join(out)
    except (ValueError, TypeError):
        return date_str


def get_responsible_party(value):
    """
        Gets a responsible party extra created by the harvesters and formats it
        nicely for the UI.

        Examples:
            [{"name": "Complex Systems Research Center", "roles": ["pointOfContact"]}]
            [{"name": "British Geological Survey", "roles": ["custodian", "pointOfContact"]},
             {"name": "Natural England", "roles": ["publisher"]}]

        Results
            Complex Systems Research Center (pointOfContact)
            British Geological Survey (custodian, pointOfContact); Natural England (publisher)
    """
    if not value:
        return None

    formatted = {
        'resourceProvider': p.toolkit._('Resource Provider'),
        'pointOfContact': p.toolkit._('Point of Contact'),
        'principalInvestigator': p.toolkit._('Principal Investigator'),
    }

    try:
        out = []
        parties = h.json.loads(value)
        for party in parties:
            roles = [formatted[role] if role in list(formatted.keys()) else p.toolkit._(role.capitalize()) for role in
                     party['roles']]
            out.append('{0} ({1})'.format(party['name'], ', '.join(roles)))
        return '; '.join(out)
    except (ValueError, TypeError):
        pass
    return value


def get_common_map_config():
    """
        Returns a dict with all configuration options related to the common
        base map (ie those starting with 'ckanext.spatial.common_map.')
    """
    namespace = 'ckanext.spatial.common_map.'
    return dict([(k.replace(namespace, ''), v) for k, v in config.items() if k.startswith(namespace)])


def strip_if_string(val):
    """
    :param val: any
    :return: str|None
    """
    if isinstance(val, str):
        val = val.strip()
        if '' == val:
            val = None
    return val


def get_export_map_json():
    """
    Reading json export map from file
    :param map_filename: str
    :return: obj
    """
    import os

    map_filename = config.get("ckanext.datajson.export_map_filename", "export.map.json")
    map_path = os.path.join(os.path.dirname(__file__), 'export_map', map_filename)

    if not os.path.isfile(map_path):
        log.warn("Could not find %s ! Please create it. Use samples from same folder", map_path)
        map_path = os.path.join(os.path.dirname(__file__), 'export_map', 'export.catalog.map.sample.json')

    with open(map_path, 'r') as export_map_json:
        json_export_map = json.load(export_map_json, object_pairs_hook=OrderedDict)

    return json_export_map


def detect_publisher(extras):
    """
    Detect publisher by package extras
    :param extras: dict
    :return: str
    """
    publisher = None

    if 'publisher' in extras and extras['publisher']:
        publisher = strip_if_string(extras['publisher'])

    for i in range(1, 6):
        key = 'publisher_' + str(i)
        if key in extras and extras[key] and strip_if_string(extras[key]):
            publisher = strip_if_string(extras[key])
    return publisher


def is_redacted(value):
    """
    Checks if value is valid POD v1.1 [REDACTED-*]
    :param value: str
    :return: bool
    """
    return isinstance(value, str) and REDACTED_REGEX.match(value)


def get_validator(schema_type="federal-v1.1", level='dataset.json'):
    """
    Get POD json validator object
    :param schema_type: str
    :return: obj
    """
    import os
    from jsonschema import Draft4Validator, FormatChecker

    schema_path = os.path.join(os.path.dirname(__file__), 'pod_schema', schema_type, level)
    with open(schema_path, 'r') as schema:
        schema = json.loads(schema.read())
        return Draft4Validator(schema, format_checker=FormatChecker())


def uglify(key):
    """
    lower string and remove spaces
    :param key: string
    :return: string
    """
    if isinstance(key, str):
        return "".join(key.lower().split()).replace('_', '').replace('-', '')
    return key


def get_extra(package, key, default=None):
    """
    Retrieves the value of an extras field.
    """
    return packageExtraCache.get(package, key, default)


def get_additional_formats():
    import os
    format_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'additional_resource_formats.json')
    resource_formats = {}
    with open(format_file_path, encoding='utf-8') as format_file:
        file_resource_formats = json.loads(format_file.read())
        for format_line in file_resource_formats:
            if format_line[0] == '_comment':
                continue
            line = [format_line[2], format_line[0], format_line[1]]
            resource_formats[format_line[0].lower()] = line

    return resource_formats


class PackageExtraCache(object):
    def __init__(self):
        self.pid = None
        self.extras = {}
        pass

    def store(self, package):
        import sys
        import os

        try:
            self.pid = package.get('id')

            current_extras = package.get('extras')
            new_extras = {}
            for extra in current_extras:
                if 'extras_rollup' == extra.get('key'):
                    rolledup_extras = json.loads(extra.get('value'))
                    for k, value in rolledup_extras.items():
                        if isinstance(value, (list, tuple)):
                            value = ", ".join(map(str, value))
                        new_extras[uglify(k)] = value
                else:
                    value = extra.get('value')
                    if isinstance(value, (list, tuple)):
                        value = ", ".join(map(str, value))
                    new_extras[uglify(extra['key'])] = value

            self.extras = new_extras
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error("%s : %s : %s : %s", exc_type, filename, exc_tb.tb_lineno, str(e))
            raise e

    def get(self, package, key, default=None):
        if self.pid != package.get('id'):
            self.store(package)
        return strip_if_string(self.extras.get(uglify(key), default))


packageExtraCache = PackageExtraCache()
