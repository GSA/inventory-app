import sys


class _CKANToolkitTests(object):
    def __getattr__(self, name):
        try:
            import ckan.new_tests as tests
        except ImportError:
            from ckan import tests
        return getattr(tests, name)

# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = _CKANToolkitTests()
