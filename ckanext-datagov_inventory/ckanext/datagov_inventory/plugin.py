import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging


log = logging.getLogger(__name__)

default_message = 'You must login to perform this action.'
@plugins.toolkit.auth_disallow_anonymous_access
def group_list(context, data_dict=None):
    return {'success': False, msg: default_message}


@plugins.toolkit.auth_disallow_anonymous_access
def package_search(context, data_dict=None):
    return {'success': False, msg: default_message}


@plugins.toolkit.auth_disallow_anonymous_access
def package_list(context, data_dict=None):
    return {'success': False, msg: default_message}


@plugins.toolkit.auth_disallow_anonymous_access
def site_read(context, data_dict=None):
    return {'success': False, msg: default_message}


# resources should be the only 'action' that defaults to True
@plugins.toolkit.auth_allow_anonymous_access
def resource_show(context, data_dict=None):
    log.info('Calling resource show')
    return {'success': False, msg: default_message}


@plugins.toolkit.auth_allow_anonymous_access
def resource_view_show(context, data_dict=None):
    log.info('Calling Resource View')
    return {'success': False, msg: default_message}


@plugins.toolkit.auth_allow_anonymous_access
def resource_read(context, data_dict=None):
    log.info('Calling Resource Read')
    return {'success': False, msg: default_message}


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'group_list': group_list,
                'package_list': package_list,
                'package_search': package_search,
                'resource_read': resource_read,
                'resource_show': resource_show,
                'resource_view_show': resource_view_show,
                'site_read': site_read
                }
