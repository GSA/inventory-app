import copy
from logging import getLogger
import re

import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.lib.navl.validators as ckan_validators

log = getLogger(__name__)

REDACTION_STROKE_REGEX = re.compile(
    r'(\[\[REDACTED-EX B[\d]\]\])'
)


def public_access_level_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(r'^(public)|(restricted public)|(non-public)$')
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match public access level validators.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def bureau_code_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(r'^\d{3}:\d{2}(\s*,\s*\d{3}:\d{2}\s*)*$')
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match bureau code format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def program_code_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(r'^\d{3}:\d{3}(\s*,\s*\d{3}:\d{3}\s*)*$')
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match program code format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def temporal_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(r'^([\-\dTWRZP/YMWDHMS:\+]{3,}/[\-\dTWRZP/YMWDHMS:\+]{3,})|(\[\[REDACTED).*?(\]\])$')
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match temporal format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def release_date_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(
            r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
            r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
            r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?|(\[\[REDACTED).*?(\]\])$'
        )
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match release date format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def accrual_periodicity_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(
            r'^([Dd]ecennial)|([Qq]uadrennial)|([Aa]nnual)|([Bb]imonthly)|([Ss]emiweekly)|([Dd]aily)|([Bb]iweekly)'
            r'|([Ss]emiannual)|([Bb]iennial)|([Tt]riennial)|([Tt]hree times a week)|([Tt]hree times a month)'
            r'|(Continuously updated)|([Mm]onthly)|([Qq]uarterly)|([Ss]emimonthly)|([Tt]hree times a year)'
            r'|R\/P(?:(\d+(?:[\.,]\d+)?)Y)?(?:(\d+(?:[\.,]\d+)?)M)?(?:(\d+(?:[\.,]\d+)?)D)?(?:T(?:(\d+(?:[\.,]\d+)'
            r'?)H)?(?:(\d+(?:[\.,]\d+)?)M)?(?:(\d+(?:[\.,]\d+)?)S)?)?$'  # ISO 8601 duration
            r'|([Ww]eekly)|([Hh]ourly)|([Cc]ompletely irregular)|([Ii]rregular)|(\[\[REDACTED).*?(\]\])$'
        )
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match accrual periodicity format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def language_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(
            r'^(((([A-Za-z]{2,3}(-([A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})(-([A-Za-z]{4}))?'
            r'(-([A-Za-z]{2}|[0-9]{3}))?(-([A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(-([0-9A-WY-Za-wy-z]'
            r'(-[A-Za-z0-9]{2,8})+))*(-(x(-[A-Za-z0-9]{1,8})+))?)|(x(-[A-Za-z0-9]{1,8})+)|((en-GB-oed'
            r'|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo|i-navajo|i-pwn|i-tao|i-tay|i-tsu'
            r'|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min'
            r'|zh-min-nan|zh-xiang)))$'
        )
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match language format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def primary_it_investment_uii_validator(regex_candidate):
    if type(regex_candidate) == str:
        validator = re.compile(r'^([0-9]{3}-[0-9]{9})|(\[\[REDACTED).*?(\]\])$')
        if isinstance(validator.match(regex_candidate), type(re.match("", ""))):
            return regex_candidate
        return p.toolkit.Invalid("Doesn't match primary it investment uii format.")

    # The regex_candidate already has validation errors, so just pass the errors through
    return regex_candidate


def string_length_validator(max=100):
    def string_validator(value):
        try:
            if len(value) <= max:
                return value
            else:
                return p.toolkit.Invalid(("Attribute is too long. (character limit = %s)" % str(max)))
        except TypeError:
            # The given value is already invalid from another validator
            return value

    return string_validator


def string(value):
    return str(value)


# excluded title, description, tags and last update as they're part of the default ckan dataset metadata
required_metadata = (
    {'id': 'title', 'validators': [ckan_validators.not_empty, string]},
    {'id': 'notes', 'validators': [ckan_validators.not_empty, string]},
    {'id': 'publisher', 'validators': [ckan_validators.not_empty, string, string_length_validator(max=300)]},
    {'id': 'contact_name', 'validators': [ckan_validators.not_empty, string, string_length_validator(max=300)]},
    {'id': 'contact_email', 'validators': [ckan_validators.not_empty, string, string_length_validator(max=200)]},
    # TODO should this unique_id be validated against any other unique IDs for this agency?
    {'id': 'unique_id', 'validators': [ckan_validators.not_empty, string, string_length_validator(max=100)]},
    {'id': 'modified', 'validators': [ckan_validators.not_empty, string, string_length_validator(max=100)]},
    {'id': 'public_access_level', 'validators': [string, public_access_level_validator]},
    {'id': 'bureau_code', 'validators': [string, bureau_code_validator, string_length_validator(max=2100)]},
    {'id': 'program_code', 'validators': [string, program_code_validator, string_length_validator(max=2100)]}
)


# used to bypass validation on create
required_metadata_update = (
    {'id': 'public_access_level', 'validators': [string, public_access_level_validator]},
    {'id': 'publisher', 'validators': [string_length_validator(max=300)]},
    {'id': 'contact_name', 'validators': [string_length_validator(max=300)]},
    {'id': 'contact_email', 'validators': [string_length_validator(max=200)]},
    # TODO should this unique_id be validated against any other unique IDs for this agency?
    {'id': 'unique_id', 'validators': [string_length_validator(max=100)]},
    {'id': 'modified', 'validators': [string_length_validator(max=100)]},
    {'id': 'bureau_code', 'validators': [string, bureau_code_validator]},
    {'id': 'program_code', 'validators': [string, program_code_validator]}
)

# some of these could be excluded (e.g. related_documents) which can be captured from other ckan default data
expanded_metadata = (
    # issued
    {'id': 'release_date', 'validators': [string, release_date_validator]},
    {'id': 'accrual_periodicity', 'validators': [string, accrual_periodicity_validator]},
    {'id': 'language', 'validators': [string, language_validator]},
    {'id': 'data_quality', 'validators': [string_length_validator(max=1000)]},
    {'id': 'publishing_status', 'validators': [string_length_validator(max=1000)]},
    {'id': 'is_parent', 'validators': [string_length_validator(max=1000)]},
    {'id': 'parent_dataset', 'validators': [string_length_validator(max=1000)]},
    # theme
    {'id': 'category', 'validators': [string_length_validator(max=1000)]},
    # describedBy
    {'id': 'related_documents', 'validators': [string_length_validator(max=2100)]},
    {'id': 'conforms_to', 'validators': [string_length_validator(max=2100)]},
    {'id': 'homepage_url', 'validators': [string_length_validator(max=2100)]},
    {'id': 'system_of_records', 'validators': [string_length_validator(max=2100)]},
    {'id': 'primary_it_investment_uii', 'validators': [primary_it_investment_uii_validator,
                                                       string_length_validator(max=2100)]},
    {'id': 'publisher_1', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_2', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_3', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_4', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_5', 'validators': [string_length_validator(max=300)]}
)

exempt_allowed = [
    'title',
    'notes',
    'tag_string',
    'modified',
    'bureau_code',
    'program_code',
    'contact_name',
    'contact_email',
    'data_quality',
    'license_new',
    'spatial',
    'temporal',
    'category',
    'data_dictionary',
    'data_dictionary_type',
    'accrual_periodicity',
    'conforms_to',
    'homepage_url',
    'language',
    'publisher',
    'primary_it_investment_uii',
    'related_documents',
    'release_date',
    'system_of_records'
]

for field in exempt_allowed:
    expanded_metadata += ({'id': 'redacted_' + field, 'validators': [string_length_validator(max=300)]},)

# excluded download_url, endpoint, format and license as they may be discoverable
required_if_applicable_metadata = (
    {'id': 'data_dictionary', 'validators': [string_length_validator(max=2048)]},
    {'id': 'data_dictionary_type', 'validators': [string_length_validator(max=2100)]},
    {'id': 'spatial', 'validators': [string_length_validator(max=500)]},
    {'id': 'temporal', 'validators': [temporal_validator]},
    {'id': 'access_level_comment', 'validators': [string_length_validator(max=255)]},
    {'id': 'license_new', 'validators': [string_length_validator(max=2100)]}
)

# used for by passing API validation
expanded_metadata_by_pass_validation = (
    # issued
    {'id': 'release_date', 'validators': [string_length_validator(max=2100)]},
    {'id': 'accrual_periodicity', 'validators': [string_length_validator(max=2100)]},
    {'id': 'language', 'validators': [string_length_validator(max=2100)]},
    {'id': 'data_quality', 'validators': [string_length_validator(max=1000)]},
    {'id': 'publishing_status', 'validators': [string_length_validator(max=1000)]},
    {'id': 'is_parent', 'validators': [string_length_validator(max=1000)]},
    {'id': 'parent_dataset', 'validators': [string_length_validator(max=1000)]},
    # theme
    {'id': 'category', 'validators': [string_length_validator(max=1000)]},
    # describedBy
    {'id': 'related_documents', 'validators': [string_length_validator(max=2100)]},
    {'id': 'conforms_to', 'validators': [string_length_validator(max=2100)]},
    {'id': 'homepage_url', 'validators': [string_length_validator(max=2100)]},
    {'id': 'rss_feed', 'validators': [string_length_validator(max=2100)]},
    {'id': 'system_of_records', 'validators': [string_length_validator(max=2100)]},
    {'id': 'system_of_records_none_related_to_this_dataset', 'validators': [string_length_validator(max=2100)]},
    {'id': 'primary_it_investment_uii', 'validators': [string_length_validator(max=2100)]},
    {'id': 'webservice', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_1', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_2', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_3', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_4', 'validators': [string_length_validator(max=300)]},
    {'id': 'publisher_5', 'validators': [string_length_validator(max=300)]}
)

# used for by passing API validation
required_if_applicable_metadata_by_pass_validation = (
    {'id': 'data_dictionary', 'validators': [string_length_validator(max=2048)]},
    {'id': 'data_dictionary_type', 'validators': [string_length_validator(max=2100)]},
    {'id': 'endpoint', 'validators': [string_length_validator(max=2100)]},
    {'id': 'spatial', 'validators': [string_length_validator(max=500)]},
    {'id': 'temporal', 'validators': [string_length_validator(max=500)]},
    {'id': 'access_level_comment', 'validators': [string_length_validator(max=255)]},
    {'id': 'license_new', 'validators': [string_length_validator(max=2100)]}
)

accrual_periodicity = [u"Decennial", u"Quadrennial", u"Annual", u"Bimonthly", u"Semiweekly", u"Daily", u"Biweekly",
                       u"Semiannual", u"Biennial", u"Triennial",
                       u"Three times a week", u"Three times a month", u"Continuously updated", u"Monthly", u"Quarterly",
                       u"Semimonthly", u"Three times a year", u"Weekly", u"Hourly", u"Irregular"]

access_levels = ['public', 'restricted public', 'non-public']

publishing_status_options = ['Published', 'Draft']

license_options = {'': '',
                   'https://www.usa.gov/publicdomain/label/1.0/': 'http://www.usa.gov/publicdomain/label/1.0/',
                   'http://creativecommons.org/publicdomain/zero/1.0/': 'http://creativecommons.org/publicdomain/zero/1.0/',
                   'http://opendatacommons.org/licenses/pddl/': 'http://opendatacommons.org/licenses/pddl/',
                   'http://opendatacommons.org/licenses/by/1-0/': 'http://opendatacommons.org/licenses/by/1-0/',
                   'http://opendatacommons.org/licenses/odbl/': 'http://opendatacommons.org/licenses/odbl/',
                   'https://creativecommons.org/licenses/by/4.0': 'https://creativecommons.org/licenses/by/4.0',
                   'https://creativecommons.org/licenses/by-sa/4.0': 'https://creativecommons.org/licenses/by-sa/4.0',
                   'http://www.gnu.org/licenses/fdl-1.3.en.html0': 'http://www.gnu.org/licenses/fdl-1.3.en.html'}

data_quality_options = {'': '', 'true': 'Yes', 'false': 'No'}
is_parent_options = {'true': 'Yes', 'false': 'No'}

# Dictionary of all media types
# media_types = json.loads(open(os.path.join(os.path.dirname(__file__), 'media_types.json'), 'r').read())

# list(set(x)) returns list with unique values
media_types_dict = h.resource_formats()
media_types = list(set([row[1] for row in list(h.resource_formats().values())]))


# all required_metadata should be required
def get_req_metadata_for_create():
    log.debug('get_req_metadata_for_create')
    new_req_meta = copy.copy(required_metadata)
    validator = ckan_validators.not_empty
    for meta in new_req_meta:
        meta['validators'].append(validator)
    return new_req_meta


# used to bypass validation on create
def get_req_metadata_for_update():
    log.debug('get_req_metadata_for_update')
    new_req_meta = copy.copy(required_metadata_update)
    validator = ckan_validators.ignore_missing
    for meta in new_req_meta:
        meta['validators'].insert(0, validator)
    return new_req_meta


def get_req_metadata_for_show_update():
    new_req_meta = copy.copy(required_metadata)
    validator = ckan_validators.ignore_missing
    for meta in new_req_meta:
        meta['validators'].insert(0, validator)
    return new_req_meta


for meta in required_if_applicable_metadata:
    meta['validators'].insert(0, ckan_validators.ignore_missing)

for meta in expanded_metadata:
    meta['validators'].insert(0, ckan_validators.ignore_missing)

for meta in required_if_applicable_metadata_by_pass_validation:
    meta['validators'].insert(0, ckan_validators.ignore_missing)

for meta in expanded_metadata_by_pass_validation:
    meta['validators'].insert(0, ckan_validators.ignore_missing)

schema_updates_for_create = [{meta['id']: meta['validators'] + [p.toolkit.get_converter('convert_to_extras')]} for meta
                             in (get_req_metadata_for_create() + required_if_applicable_metadata + expanded_metadata)]
schema_updates_for_update = [{meta['id']: meta['validators'] + [p.toolkit.get_converter('convert_to_extras')]} for meta
                             in (get_req_metadata_for_update() + required_if_applicable_metadata + expanded_metadata)]
schema_updates_for_show = [{meta['id']: meta['validators'] + [p.toolkit.get_converter('convert_from_extras')]} for meta
                           in
                           (get_req_metadata_for_show_update() + required_if_applicable_metadata + expanded_metadata)]
schema_api_for_create = [{meta['id']: meta['validators'] + [p.toolkit.get_converter('convert_to_extras')]} for meta
                         in (required_if_applicable_metadata_by_pass_validation + expanded_metadata_by_pass_validation)]
