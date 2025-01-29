import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from ckan.model import User
from ckan.common import _, g, current_user, request as ckan_request
import ckan.lib.base as base
from ckan.logic.auth import get_resource_object
from ckan.logic.auth.get import package_show
from ckan.plugins.toolkit import config
import ckan.authz as authz

from flask import Blueprint, redirect
import logging
import re

log = logging.getLogger(__name__)
pusher = Blueprint('datagov_inventory', __name__)


@toolkit.auth_allow_anonymous_access
@toolkit.chained_auth_function
def restrict_anon_access(next_auth, context, data_dict):
    if context["user"]:
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
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    def get_auth_functions(self):
        return {'format_autocomplete': restrict_anon_access,
                'group_list': restrict_anon_access,
                'license_list': restrict_anon_access,
                'member_roles_list': restrict_anon_access,
                'organization_list': restrict_anon_access,
                'package_list': restrict_anon_access,
                'package_search': restrict_anon_access,
                'package_show': inventory_package_show,
                'resource_show': inventory_resource_show,
                'tag_list': restrict_anon_access,
                'tag_show': restrict_anon_access,
                'task_status_show': restrict_anon_access,
                'user_list': restrict_anon_access,
                'user_show': restrict_anon_access,
                'vocabulary_list': restrict_anon_access,
                'vocabulary_show': restrict_anon_access,
                }

    # render our custom 403 template
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('fanstatic', 'datagov_inventory')

    # IBlueprint
    def get_blueprint(self):
        return pusher


def redirect_homepage():
    if current_user.is_authenticated or g.user:
        CKAN_SITE_URL = config.get("ckan.site_url")
        return redirect(CKAN_SITE_URL + '/dataset/', code=302)
    else:
        return base.render(u'error/anonymous.html')


pusher.add_url_rule('/', view_func=redirect_homepage)

@pusher.before_app_request
def check_dataset_access():
    if toolkit.request.path in ('/dataset/', '/dataset'):
        if not current_user.is_authenticated and not g.user:
            return base.render(u'error/anonymous.html'), 403
