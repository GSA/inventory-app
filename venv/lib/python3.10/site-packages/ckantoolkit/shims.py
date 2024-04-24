import json

from six import text_type

from ckan.lib.navl.dictization_functions import missing

try:
    # CKAN >= 2.6
    from ckan.common import config
except ImportError:
    # CKAN < 2.6
    from pylons import config


class HelpersNoMagic(object):
    """
    Access helper.functions as attributes, but raise AttributeError
    for missing functions instead of returning null_function

    adapted from ckan/config/environment.py:_HelpersNoMagic
    """

    def __getattr__(self, name):
        h = config["pylons.h"]

        fn = getattr(h, name)
        if fn == h.null_function:
            raise AttributeError("No helper found named '%s'" % name)
        return fn


def unicode_safe(value):
    """

    **Starting from CKAN 2.8 this is included in CKAN core**

    Make sure value passed is treated as unicode, but don't raise
    an error if it's not, just make a reasonable attempt to
    convert other types passed.

    This validator is a safer alternative to the old ckan idiom
    of using the unicode() function as a validator. It tries
    not to pollute values with Python repr garbage e.g. when passed
    a list of strings (uses json format instead). It also
    converts binary strings assuming either UTF-8 or CP1252
    encodings (not ASCII, with occasional decoding errors)
    """
    if isinstance(value, text_type):
        return value
    if hasattr(value, "filename"):
        # cgi.FieldStorage instance for uploaded files, show the name
        value = value.filename
    if value is missing or value is None:
        return u""
    if isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            return value.decode(u"utf8")
        except UnicodeDecodeError:
            return value.decode(u"cp1252")
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    except Exception:
        # at this point we have given up. Just don't error out
        try:
            return text_type(value)
        except Exception:
            return u"\N{REPLACEMENT CHARACTER}"
