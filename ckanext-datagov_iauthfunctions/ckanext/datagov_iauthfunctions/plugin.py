import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datagov_iauthfunctions')

    def read(self, entity):
        '''
        IPackageController.read && IOrganizationController.read
        page must not be accessible by visitors
        '''
        visitor_allowed_actions = [
            'resource_download',  # download resource file
            'resource_read',  # resource read page
            'resource_view'  # resource view (data explorer)
        ]
        if not c.user and c.action not in visitor_allowed_actions:
            abort(401, _('Not authorized to see this page'))
            
    def before_search(self, search_params):
        '''
        IPackageController.search
        page must not be accessible by visitors
        '''
        if not c.user:
            abort(401, _('Not authorized to see this page'))

        return search_params