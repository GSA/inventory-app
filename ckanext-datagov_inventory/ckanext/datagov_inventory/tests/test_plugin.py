"""Tests for datagov_inventory plugin.py."""
import ckanext.datagov_inventory.plugin as plugin


from nose.tools import assert_in, assert_not_in

try:
    from ckan.tests.helpers import FunctionalTestBase
except ImportError:
    from ckan.new_tests.helpers import FunctionalTestBase


class TestDatagovInventory(FunctionalTestBase):

    def test_plugin(self):
        pass

    def test_datagov_inventory_navigation(self):
        app = self._get_test_app()

        index_response = app.get('/dataset')
        assert_in('<li class="active"><a href="/dataset">Data</a></li>',
                index_response.unicode_body)
        assert_in('<a class="dropdown-toggle" data-toggle="dropdown">Topics<b\n            class="caret"></b></a>',
                index_response.unicode_body)
        assert_in('<li><a href="//resources.data.gov">Resources</a></li>',
                index_response.unicode_body)
        assert_in('<li><a href="//strategy.data.gov">Strategy</a></li>',
                index_response.unicode_body)
        assert_in('<li><a href="//www.data.gov/developers/">Developers</a></li>',
                index_response.unicode_body)
        assert_in('<li><a href="//www.data.gov/contact">Contact</a></li>',
                index_response.unicode_body)
