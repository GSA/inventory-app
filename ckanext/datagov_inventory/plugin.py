import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from ckan.model import User
from ckan.common import _, request as ckan_request
from ckan.logic.auth import get_resource_object
from ckan.logic.auth.get import package_show
from ckan.common import current_user
import ckan.authz as authz
import logging
import re

log = logging.getLogger(__name__)


@toolkit.auth_allow_anonymous_access
@toolkit.chained_auth_function
def restrict_anon_access(next_auth, context, data_dict):
    if current_user.is_authenticated:
        return next_auth(context, data_dict)
    else:
        return {'success': False}

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
