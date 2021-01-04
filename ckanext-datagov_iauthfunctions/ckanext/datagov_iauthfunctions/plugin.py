import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


default_message = 'You must be logged to perform this action.'

def redirect_to_login():
    return redirect("http://www.example.com", code=302)


@plugins.toolkit.auth_allow_anonymous_access
def group_list(context, data_dict=None):
    user_name = context['user']

    if user_name:
        return {'success' : True}
    else:
        return {'success' : False, 'msg' : default_message}

@plugins.toolkit.auth_allow_anonymous_access
def site_read(context, data_dict=None):
    user_name = context['user']

    if user_name:
        return {'success' : True}
    else:
        return {'success' : False, 'msg' : default_message}

# resources should be the only 'action' that defaults to True
@plugins.toolkit.auth_allow_anonymous_access
def resource_download(context, data_dict=None):
    return {'success' : True}

@plugins.toolkit.auth_allow_anonymous_access
def resource_read(context, data_dict=None):
    return {'success' : True}

@plugins.toolkit.auth_allow_anonymous_access
def resource_view(context, data_dict=None):
    return {'success' : True}

class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'group_list' : group_list,
                'site_read' : site_read,
                'resource_download' : resource_download,
                'resource_read' : resource_read,
                'resource_view' : resource_view}