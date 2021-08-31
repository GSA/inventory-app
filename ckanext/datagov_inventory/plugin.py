import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
# import ckan.authz as authz
import logging


log = logging.getLogger(__name__)

# starting auth functions.
# Most auth functions should only allow logged in users to access.


# Implemented as a decorator
def datagov_disallow_anonymous_access(func=None):
    @toolkit.chained_auth_function
    @toolkit.auth_disallow_anonymous_access
    def _wrapper(next_auth, context, dict_data=None):
        if func:
            # We're called in the decorator context, call the function
            return func(next_auth, context, dict_data)
        else:
            # We were called as a function, just call the next_auth function
            return next_auth(context, dict_data)

    # We're always applying the auth_disallow_anonymous_access decorator.
    return _wrapper


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)

    def get_auth_functions(self):
        return {'format_autocomplete': datagov_disallow_anonymous_access(),
                'group_list': datagov_disallow_anonymous_access(),
                'group_list_authz': datagov_disallow_anonymous_access(),
                'license_list': datagov_disallow_anonymous_access(),
                'member_roles_list': datagov_disallow_anonymous_access(),
                'organization_list': datagov_disallow_anonymous_access(),
                'package_list': datagov_disallow_anonymous_access(),
                'package_search': datagov_disallow_anonymous_access(),
                'site_read': datagov_disallow_anonymous_access(),
                'tag_list': datagov_disallow_anonymous_access(),
                'tag_show': datagov_disallow_anonymous_access(),
                'task_status_show': datagov_disallow_anonymous_access(),
                'vocabulary_list': datagov_disallow_anonymous_access(),
                'vocabulary_show': datagov_disallow_anonymous_access(),
                }

    # render our custom 403 template
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
