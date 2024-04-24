import csv
import os
import re
import rfc3987 as rfc3987_url

# from the iso8601 package, plus ^ and $ on the edges
ISO8601_REGEX = re.compile(r"^([0-9]{4})(-([0-9]{1,2})(-([0-9]{1,2})"
                           r"((.)([0-9]{2}):([0-9]{2})(:([0-9]{2})(\.([0-9]+))?)?"
                           r"(Z|(([-+])([0-9]{2}):([0-9]{2})))?)?)?)?$")

TEMPORAL_REGEX_1 = re.compile(
    r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
    r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?(\/)([\+-]?\d{4}'
    r'(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|'
    r'(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

TEMPORAL_REGEX_2 = re.compile(
    r'^(R\d*\/)?([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\4([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])'
    r'(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)'
    r'([\.,]\d+(?!:))?)?(\18[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?(\/)'
    r'P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+(?:\.\d+)?H)?'
    r'(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?$'
)

TEMPORAL_REGEX_3 = re.compile(
    r'^(R\d*\/)?P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+'
    r'(?:\.\d+)?H)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?\/([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])'
    r'(\4([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))'
    r'([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]\d+(?!:))?)?(\18[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])'
    r'([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

MODIFIED_REGEX_1 = re.compile(
    r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
    r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

MODIFIED_REGEX_2 = re.compile(
    r'^(R\d*\/)?P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+(?:\.\d+)?H)?'
    r'(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?$'
)

MODIFIED_REGEX_3 = re.compile(
    r'^(R\d*\/)?([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\4([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|'
    r'(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]\d+(?!:))?)?'
    r'(\18[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?(\/)P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?'
    r'(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+(?:\.\d+)?H)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?$'
)

ISSUED_REGEX = re.compile(
    r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
    r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

PROGRAM_CODE_REGEX = re.compile(r"^[0-9]{3}:[0-9]{3}$")

IANA_MIME_REGEX = re.compile(r"^[-\w]+/[-\w]+(\.[-\w]+)*([+][-\w]+)?$")

PRIMARY_IT_INVESTMENT_UII_REGEX = re.compile(r"^[0-9]{3}-[0-9]{9}$")

ACCRUAL_PERIODICITY_VALUES = (
    None, "R/P10Y", "R/P4Y", "R/P1Y", "R/P2M", "R/P3.5D", "R/P1D", "R/P2W", "R/P0.5W", "R/P6M",
    "R/P2Y", "R/P3Y", "R/P0.33W", "R/P0.33M", "R/PT1S", "R/PT1S", "R/P1M", "R/P3M",
    "R/P0.5M", "R/P4M", "R/P1W", "R/PT1H", "irregular")

LANGUAGE_REGEX = re.compile(
    r'^(((([A-Za-z]{2,3}(-([A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})(-([A-Za-z]{4}))?'
    r'(-([A-Za-z]{2}|[0-9]{3}))?(-([A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(-([0-9A-WY-Za-wy-z](-[A-Za-z0-9]{2,8})+))*'
    r'(-(x(-[A-Za-z0-9]{1,8})+))?)|(x(-[A-Za-z0-9]{1,8})+)|'
    r'((en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo'
    r'|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|'
    r'(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang)))$'
)

REDACTED_REGEX = re.compile(
    r'^(\[\[REDACTED).*?(\]\])$'
)

# load the OMB bureau codes on first load of this module
omb_burueau_codes = set()
# for row in csv.DictReader(urllib.urlopen("https://resources.data.gov/schemas/dcat-us/v1.1/omb_bureau_codes.csv")):
#    omb_burueau_codes.add(row["Agency Code"] + ":" + row["Bureau Code"])

with open(os.path.join(os.path.dirname(__file__), "resources", "omb_bureau_codes.csv"), "r") as csvfile:
    for row in csv.DictReader(csvfile):
        omb_burueau_codes.add(row["Agency Code"] + ":" + row["Bureau Code"])


def add_error(errs, severity, heading, description, context=None):
    s = errs.setdefault((severity, heading), {}).setdefault(description, set())
    if context:
        s.add(context)


def nice_type_name(data_type):
    if data_type == (str, str) or data_type in (str, str):
        return "string"
    elif data_type == list:
        return "array"
    else:
        return str(data_type)


def check_required_field(obj, field_name, data_type, dataset_name, errs):
    # checks that a field exists and has the right type
    if field_name not in obj:
        add_error(errs, 10, "Missing Required Fields", "The '%s' field is missing." % field_name, dataset_name)
        return False
    elif obj[field_name] is None:
        add_error(errs, 10, "Missing Required Fields", "The '%s' field is empty." % field_name, dataset_name)
        return False
    elif not isinstance(obj[field_name], data_type):
        add_error(errs, 5, "Invalid Required Field Value",
                  "The '%s' field must be a %s but it has a different datatype (%s)." % (
                      field_name, nice_type_name(data_type), nice_type_name(type(obj[field_name]))), dataset_name)
        return False
    elif isinstance(obj[field_name], list) and len(obj[field_name]) == 0:
        add_error(errs, 10, "Missing Required Fields", "The '%s' field is an empty array." % field_name, dataset_name)
        return False
    return True


def check_required_string_field(obj, field_name, min_length, dataset_name, errs):
    # checks that a required field exists, is typed as a string, and has a minimum length
    if not check_required_field(obj, field_name, (str, str), dataset_name, errs):
        return False
    elif len(obj[field_name].strip()) == 0:
        add_error(errs, 10, "Missing Required Fields", "The '%s' field is present but empty." % field_name,
                  dataset_name)
        return False
    elif len(obj[field_name].strip()) < min_length:
        add_error(errs, 100, "Invalid Field Value",
                  "The '%s' field is very short (min. %d): \"%s\"" % (field_name, min_length, obj[field_name]),
                  dataset_name)
        return False
    return True


def is_redacted(field):
    if isinstance(field, str) and REDACTED_REGEX.match(field):
        return True
    return False


def check_url_field(required, obj, field_name, dataset_name, errs, allow_redacted=False):
    # checks that a required or optional field, if specified, looks like a URL
    if not required and (field_name not in obj or obj[field_name] is None):
        return True  # not required, so OK
    if not check_required_field(obj, field_name, (str, str), dataset_name, errs):
        return False  # just checking data type
    if allow_redacted and is_redacted(obj[field_name]):
        return True
    if not rfc3987_url.match(obj[field_name]):
        add_error(errs, 5, "Invalid Required Field Value",
                  "The '%s' field has an invalid rfc3987 URL: \"%s\"." % (field_name, obj[field_name]), dataset_name)
        return False
    return True
