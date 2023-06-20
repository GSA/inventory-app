import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import current_user
import logging

log = logging.getLogger(__name__)


@toolkit.auth_allow_anonymous_access
@toolkit.chained_auth_function
def restrict_anon_access(next_auth, context, data_dict):
    if current_user.is_authenticated:
        return next_auth(context, data_dict)
    else:
        return {'success': False}


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)

    def get_auth_functions(self):
        return {'group_list': restrict_anon_access,
                'organization_list': restrict_anon_access,
                'site_read': restrict_anon_access,
                }

    # render our custom 403 template
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('fanstatic', 'datagov_inventory')
