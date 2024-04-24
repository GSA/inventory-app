import flask
import logging
import ckan.plugins as p
import ckan.lib.helpers as h

__author__ = 'GSA'

log = logging.getLogger('ckanext.googleanalytics-basic')

p.toolkit.requires_ckan_version("2.9")


class GoogleAnalyticsBasicException(Exception):
    pass


class GoogleAnalyticsBasicPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.ITemplateHelpers)

    def configure(self, config):
        '''Load config settings for this extension from config file.

        See IConfigurable.

        '''
        self.googleanalytics_ids = []
        if 'googleanalytics.ids' not in config:
            msg = "Missing googleanalytics.ids in config"
            log.warn(msg)
            return
            # raise GoogleAnalyticsBasicException(msg)

        self.googleanalytics_ids = config['googleanalytics.ids'].split()

        app = flask.Flask(__name__)
        app.config['SERVER_NAME'] = "app"
        with app.app_context(), app.test_request_context():
            self.googleanalytics_javascript_url = h.url_for_static(
                '/scripts/ckanext-googleanalytics.js')

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('fanstatic', 'googleanalyticsbasic')

    def get_helpers(self):
        '''Return the CKAN 2.0 template helper functions this plugin provides.

        See ITemplateHelpers.

        '''
        return {'googleanalyticsbasic_header': self.googleanalyticsbasic_header}

    def googleanalyticsbasic_header(self):
        '''Render the googleanalytics_header snippet for CKAN 2.0 templates.

        This is a template helper function that renders the
        googleanalytics_header jinja snippet. To be called from the jinja
        templates in this extension, see ITemplateHelpers.

        Using enumerate() to implement multiple trackers support
        https://developers.google.com/analytics/devguides/collection/analyticsjs/advanced#multipletrackers

        '''
        data = {
            'googleanalytics_ids': enumerate(self.googleanalytics_ids, start=1)
        }

        return p.toolkit.render_snippet(
            'snippets/googleanalyticsbasic_header.html', data)
