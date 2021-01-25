import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.authz as authz
import logging


log = logging.getLogger(__name__)


# a generic user validation function
default_message = 'You must login to perform this action.'


def validate_user(context, data_dict=None):
    user = context.get('user')
    if user:
        return {'success': True}
    else:
        return {'success': False, 'msg': default_message}

# starting auth functions.
# Most auth functions should only allow logged in users to access.


@plugins.toolkit.auth_disallow_anonymous_access
def format_autocomplete(context, data_dict=None):
    log.info('Calling format autocomplete')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def group_list(context, data_dict=None):
    log.info('Calling group list')
    return validate_user(context, data_dict)


# group list is called on anonymous pages through package_show
# this prevents a 500, and instead returns our 403 error
@plugins.toolkit.auth_allow_anonymous_access
def group_list_authz(context, data_dict=None):
    log.info('Calling group list authz')
    user = context.get('user')
    if user:
        return authz.is_authorized('group_list', context, data_dict)
    else:
        toolkit.abort(status_code=403)
        return {'success': False, 'msg': default_message}


@plugins.toolkit.auth_disallow_anonymous_access
def license_list(context, data_dict=None):
    log.info('Calling license list')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def member_roles_list(context, data_dict=None):
    log.info('Calling member roles list')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def organization_list(context, data_dict=None):
    log.info('Calling organization list')
    return validate_user(context, data_dict)


# this is already handled non-auth ckan core requests
# implementing this here causes errors in other functions calls
# ie package_search
# @plugins.toolkit.auth_disallow_anonymous_access
# def organization_list_for_user(context, data_dict=None):
#     log.info('Calling Organization List For User')
#     return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def package_search(context, data_dict=None):
    log.info('Calling package search')
    return validate_user(context, data_dict)


# Let upstream CKAN handle package_show access normally,
#   depending upon the user
# @plugins.toolkit.auth_allow_anonymous_access
# def package_show(context, data_dict):
#     return {'success' : True}


@plugins.toolkit.auth_disallow_anonymous_access
def package_list(context, data_dict=None):
    log.info('Calling package list')
    return validate_user(context, data_dict)


# resources should be the only 'action' that defaults to True
@plugins.toolkit.auth_allow_anonymous_access
def resource_show(context, data_dict=None):
    log.info('Calling resource show')
    return {'success': True}


@plugins.toolkit.auth_allow_anonymous_access
def resource_read(context, data_dict=None):
    log.info('Calling resource read')
    return {'success': True}


@plugins.toolkit.auth_allow_anonymous_access
def resource_view_list(context, data_dict=None):
    log.info('Calling resource view list')
    return {'success': True}


@plugins.toolkit.auth_allow_anonymous_access
def resource_view_show(context, data_dict=None):
    log.info('Calling resource view')
    return {'success': True}


@plugins.toolkit.auth_disallow_anonymous_access
def request_reset(context, data_dict=None):
    # Using login.gov: reject all CKAN password resets 
    log.info('Calling password request reset')
    return {'success': False}


@plugins.toolkit.auth_disallow_anonymous_access
def revision_list(context, data_dict=None):
    log.info('Calling revision list')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def revision_show(context, data_dict=None):
    log.info('Calling revision show')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def site_read(context, data_dict=None):
    log.info('Calling site read')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def tag_list(context, data_dict=None):
    log.info('Calling tag list')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def tag_show(context, data_dict=None):
    log.info('Calling tag show')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def task_status_show(context, data_dict=None):
    log.info('Calling task status show')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def user_reset(context, data_dict=None):
    log.info('Calling user reset')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def vocabulary_list(context, data_dict=None):
    log.info('Calling vocabulary list')
    return validate_user(context, data_dict)


@plugins.toolkit.auth_disallow_anonymous_access
def vocabulary_show(context, data_dict=None):
    log.info('Calling vocabulary show')
    return validate_user(context, data_dict)


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)

    def get_auth_functions(self):
        return {'format_autocomplete': format_autocomplete,
                'group_list': group_list,
                'group_list_authz': group_list_authz,
                'license_list': license_list,
                'member_roles_list': member_roles_list,
                'organization_list': organization_list,
                'package_list': package_list,
                'package_search': package_search,
                'resource_read': resource_read,
                'resource_show': resource_show,
                'resource_view_list': resource_view_list,
                'request_reset': request_reset,
                'resource_view_show': resource_view_show,
                'revision_list': revision_list,
                'revision_show': revision_show,
                'site_read': site_read,
                'tag_list': tag_list,
                'tag_show': tag_show,
                'task_status_show': task_status_show,
                'user_reset': user_reset,
                'vocabulary_list': vocabulary_list,
                'vocabulary_show': vocabulary_show,
                }

    # render our custom 403 template
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
