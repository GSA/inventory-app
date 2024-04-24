from ckan.lib import base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.plugins.toolkit import render
from ckan.common import request, c, _

from flask import Blueprint
from logging import getLogger

check_access = logic.check_access
NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
abort = base.abort

dcat_usmetadata = Blueprint('dcat_usmetadata', __name__)
log = getLogger(__name__)


def new_metadata():
    if not c.user:
        err = _('Unauthorized to create a package')
        h.flash_error(err)
        came_from = h.url_for(
            '/dataset',
            action='new_metadata')
        h.redirect_to(controller='user',
                      action='login', came_from=came_from)

    context = {'model': model, 'session': model.Session,
               'user': c.user, 'auth_user_obj': c.userobj,
               'save': 'save' in request.params}
    try:
        check_access('package_create', context)
    except NotAuthorized:
        abort(403, _('Unauthorized to create a package'))
    return render('new-metadata.html')


def edit_metadata(id):
    if not c.user:
        err = _('Unauthorized to edit a package')
        h.flash_error(err)
        came_from = h.url_for(
            '/dataset/edit-new/',
            action='edit_metadata',
            id=id)
        h.redirect_to(controller='user',
                      action='login', came_from=came_from)

    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               'save': 'save' in request.params}

    try:
        c.pkg_dict = logic.get_action('package_show')(context, {'id': id})
    except NotAuthorized:
        abort(401, _('Unauthorized to read package %s') % '')
    except NotFound:
        abort(404, _('Dataset not found'))

    try:
        check_access('package_update', context)
    except NotAuthorized:
        abort(401, _('User %r not authorized to edit %s') % (c.user, id))

    return render('new-metadata.html',
                  extra_vars={'id': c.pkg_dict.get('name', None) or c.pkg_dict.get('id', None)})


dcat_usmetadata.add_url_rule('/dataset/edit-new/<id>',
                             view_func=edit_metadata)
dcat_usmetadata.add_url_rule('/dataset/new-metadata',
                             view_func=new_metadata)
