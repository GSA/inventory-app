import sys

# XXX: required to prevent a mysterious
# "TypeError: expected string or Unicode object, NoneType found"
# in the ckan.plugins.toolkit import statement
import ckan


class _CKANToolkit(object):
    """
    Late initialization to match ckan.plugins.toolkit
    """
    __path__ = __path__

    def __getattr__(self, name):
        import ckan.plugins.toolkit as tk

        try:
            value = getattr(tk, name)
        except AttributeError:
            # backports here:
            if name == 'ungettext':
                # CKAN < 2.5
                from ckan.common import ungettext as value
            elif name == 'DefaultGroupForm':
                from ckan.lib.plugins import DefaultGroupForm as value
            elif name == 'missing':
                from ckan.lib.navl.dictization_functions import (
                    missing as value)
            elif name == 'StopOnError':
                from ckan.lib.navl.dictization_functions import (
                    StopOnError as value)
            elif name == 'DefaultOrganizationForm':
                from ckan.lib.plugins import DefaultOrganizationForm as value
            elif name == 'h':
                from ckantoolkit.shims import HelpersNoMagic
                value = HelpersNoMagic()
            elif name == 'config':
                # CKAN < 2.6
                from pylons import config as value
            elif name == 'HelperError':
                class HelperError(Exception):
                    pass
                value = HelperError
            elif name == 'unicode_safe':
                try:
                    from ckan.lib.navl.validators import unicode_safe as value
                except ImportError:
                    from ckantoolkit.shims import unicode_safe as value
            else:
                raise
        setattr(self, name, value)  # skip this function next time
        return value

    def __dir__(self):
        import ckan.plugins.toolkit as tk
        return dir(tk)


# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = _CKANToolkit()
