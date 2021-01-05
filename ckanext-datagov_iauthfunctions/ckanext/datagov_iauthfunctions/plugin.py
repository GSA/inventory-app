import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging


log = logging.getLogger(__name__)

default_message = 'You must be logged to perform this action.'

def redirect_to_login():
    log.info('Calling redirect')
    return toolkit.abort(status_code=403, detail='You must login before performing this action.')

@plugins.toolkit.auth_allow_anonymous_access
def group_list(context, data_dict=None):
    log.info('Calling group list')
    user_name = context.get('user')

    if user_name:
        return {'success' : True}
    else:
        return {'success' : False, 'msg' : default_message}

@plugins.toolkit.auth_allow_anonymous_access
def package_search(context, data_dict=None):
    log.info('Calling package list')
    user_name = context.get('user')

    if user_name:
        return {'success' : True}
    else:
        redirect_to_login()
        return {'success' : False, 'msg' : default_message}

@plugins.toolkit.auth_allow_anonymous_access
def package_list(context, data_dict=None):
    log.info('Calling package list')
    user_name = context.get('user')

    if user_name:
        return {'success' : True}
    else:
        redirect_to_login()
        return {'success' : False, 'msg' : default_message}

@plugins.toolkit.auth_allow_anonymous_access
def site_read(context, data_dict=None):
    log.info('Calling site read.')
    user_name = context.get('user')
    if user_name:
        return {'success' : True}
    else:
        redirect_to_login()
        return {'success' : False, 'msg' : default_message}

# resources should be the only 'action' that defaults to True
@plugins.toolkit.auth_allow_anonymous_access
def resource_show(context, data_dict=None):
    log.info('Calling resource show')
    return {'success' : True}

@plugins.toolkit.auth_allow_anonymous_access
def resource_view_show(context, data_dict=None):
    log.info('Calling Resource View')
    return {'success' : True}  

@plugins.toolkit.auth_allow_anonymous_access
def resource_read(context, data_dict=None):
    log.info('Calling Resource Read')
    return {'success' : True}

class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'group_list' : group_list,
                'site_read' : site_read,
                'resource_show' : resource_show,
                'resource_view_show' : resource_view_show,
                'resource_read' : resource_read,
                'package_list' : package_list,
                'package_search' : package_search
                }
