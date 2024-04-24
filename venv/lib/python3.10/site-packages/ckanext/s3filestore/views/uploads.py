# encoding: utf-8
import os
import logging

import flask
from botocore.exceptions import ClientError

import ckantoolkit as toolkit
from ckantoolkit import _
import ckan.lib.base as base

from ckanext.s3filestore.uploader import S3Uploader, BaseS3Uploader


Blueprint = flask.Blueprint
redirect = toolkit.redirect_to
abort = base.abort
log = logging.getLogger(__name__)

s3_uploads = Blueprint(
    u's3_uploads',
    __name__
)


def uploaded_file_redirect(upload_to, filename):
    '''Redirect static file requests to their location on S3.'''

    storage_path = S3Uploader.get_storage_path(upload_to)
    filepath = os.path.join(storage_path, filename)
    base_uploader = BaseS3Uploader()

    try:
        url = base_uploader.get_signed_url_to_key(filepath)
    except ClientError as ex:
        if ex.response['Error']['Code'] in ['NoSuchKey', '404']:
            return abort(404, _('Keys not found on S3'))
        else:
            raise ex

    return redirect(url)


s3_uploads.add_url_rule(u'/uploads/<upload_to>/<filename>',
                        view_func=uploaded_file_redirect)


def get_blueprints():
    return [s3_uploads]
