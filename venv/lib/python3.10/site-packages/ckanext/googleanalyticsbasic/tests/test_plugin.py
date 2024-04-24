from ckanext.googleanalyticsbasic.plugin \
    import GoogleAnalyticsBasicPlugin as GA
import inspect


class TestPlugin(object):

    def test_configure_ids(self):
        config = {'googleanalytics.ids': 'UA-TEST-1 UA-TEST-2'}
        analytics = GA()
        GA().configure(config)

        assert all(id in analytics.googleanalytics_ids
                   for id in ['UA-TEST-1', 'UA-TEST-2'])

    def test_configure_ids_not_present(self):
        config = {}
        analytics = GA()
        GA().configure(config)

        assert analytics.googleanalytics_ids == []

    def test_configure_js_url(self):
        config = {'googleanalytics.ids': 'UA-TEST-1 UA-TEST-2'}
        analytics = GA()
        GA().configure(config)

        assert analytics.googleanalytics_javascript_url \
            == '/scripts/ckanext-googleanalytics.js'

    def test_get_helpers(self):

        assert inspect.ismethod(
            GA().get_helpers()['googleanalyticsbasic_header'])
