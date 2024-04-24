try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers


class TestScript(helpers.FunctionalTestBase):

    def setup(self):
        helpers.reset_db()

    def test_fed_script_present(self):
        self.app = self._get_test_app()

        dataset_page = self.app.get('/dataset')

        assert ('<script id="_fed_an_ua_tag" src="https://dap.digitalgov.gov/'
                'Universal-Federated-Analytics-Min.js?agency=GSA&subagency=TTS"></script>') \
            in dataset_page

    def test_ga_script_present(self):
        self.app = self._get_test_app()

        dataset_page = self.app.get('/dataset')
        script = ('(function(i,s,o,g,r,a,m){i[\'GoogleAnalyticsObject\']=r;i[r'
                  ']=i[r]||function(){\n(i[r].q=i[r].q||[]).push(arguments)},i'
                  '[r].l=1*new Date();a=s.createElement(o),\nm=s.getElementsBy'
                  'TagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a'
                  ',m)\n})(window,document,\'script\',\'//www.google-analytics'
                  '.com/analytics.js\',\'ga\');')

        assert script in dataset_page

    def test_trackers_in_use(self):
        self.app = self._get_test_app()
        dataset_page = self.app.get('/dataset')

        script = "ga('create', 'UA-1010101-1', 'auto', 'tracker1');"
        assert script in dataset_page

        script = "ga('create', 'UA-1010101-2', 'auto', 'tracker2');"
        assert script in dataset_page

    def test_ga_js_script_added_to_fanstatic_present(self):
        self.app = self._get_test_app()

        dataset_page = self.app.get('/dataset')

        assert all(i in dataset_page for i in
                   ['<script src="/webassets/googleanalyticsbasic'
                    '/events.js?11759afa" type="text/javascript"></script>'])
