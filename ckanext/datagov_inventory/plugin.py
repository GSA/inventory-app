import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from ckan.model import User
from ckan.common import _, request as ckan_request
from ckan.logic.auth import get_resource_object
from ckan.logic.auth.get import package_show
import ckan.authz as authz
import logging
import re


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


@toolkit.auth_allow_anonymous_access
def test_func(context, data_dict):
    log.info('*** here ***')
    return {'success': True}

# Comes from
# https://github.com/ckan/ckan/blob/master/ckan/logic/auth/get.py#L129-L145
# Anonymous users rely on public/private package info to have access
# CKAN users utilize normal process


@toolkit.auth_allow_anonymous_access
def inventory_resource_show(context, data_dict):
    model = context['model']
    user = User.by_name(context.get('user'))
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource,'
                               ' cannot check auth.'))

    if user is None:
        if pkg.private:
            return {'success': False}
        else:
            return {'success': True}
    else:
        pkg_dict = {'id': pkg.id}
        authorized = authz.is_authorized('package_show', context, pkg_dict) \
            .get('success')

        if not authorized:
            return {'success': False,
                    'msg': _('User %s not authorized to read resource %s')
                    % (user, resource.id)}
        else:
            return {'success': True}


@toolkit.auth_allow_anonymous_access
def inventory_package_show(context, data_dict):
    model = context['model']
    user = User.by_name(context.get('user'))
    pkg = model.Package.get(data_dict.get('id', None))

    # package_show appears to be needed to download package resources.
    # but we dont want direct package_show call open to anonymous user.
    # only for download url matching /dataset/*/resource/*/download/*
    url_pattern = r"^/dataset/[0-9a-f-]{36}/resource/[0-9a-f-]{36}/download/.*"
    re_pattern = re.compile(url_pattern)
    if user is None:
        if not pkg.private and re_pattern.match(ckan_request.full_path):
            return {'success': True}
        else:
            return {'success': False}
    else:
        return package_show(context, data_dict)


class Datagov_IauthfunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)

    def get_auth_functions(self):
        return {'format_autocomplete': datagov_disallow_anonymous_access(),
                'group_list': test_func,
                'license_list': datagov_disallow_anonymous_access(),
                'member_roles_list': datagov_disallow_anonymous_access(),
                'organization_list': test_func,
                'package_list': datagov_disallow_anonymous_access(),
                'package_search': datagov_disallow_anonymous_access(),
                'package_show': datagov_disallow_anonymous_access(),
                'resource_show': datagov_disallow_anonymous_access(),
                'site_read': datagov_disallow_anonymous_access(),
                'tag_list': datagov_disallow_anonymous_access(),
                'tag_show': datagov_disallow_anonymous_access(),
                'task_status_show': datagov_disallow_anonymous_access(),
                'user_list': datagov_disallow_anonymous_access(),
                'user_show': datagov_disallow_anonymous_access(),
                'vocabulary_list': datagov_disallow_anonymous_access(),
                'vocabulary_show': datagov_disallow_anonymous_access(),
                }

    # render our custom 403 template
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('fanstatic', 'datagov_inventory')
