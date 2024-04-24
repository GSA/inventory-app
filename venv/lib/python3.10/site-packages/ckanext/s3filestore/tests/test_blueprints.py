# encoding: utf-8
import six
import requests

import pytest

from ckantoolkit import config
import ckan.tests.factories as factories
from ckan.lib.helpers import url_for


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
class TestS3Controller(object):

    @classmethod
    def setup_class(cls):
        cls.bucket_name = config.get(u'ckanext.s3filestore.aws_bucket_name')

    def test_resource_download_url(self, resource_with_upload):
        u'''The resource url is expected for uploaded resource file.'''

        expected_url = u'http://test.ckan.net/dataset/{0}/' \
                       u'resource/{1}/download/test.csv'.\
            format(resource_with_upload[u'package_id'],
                   resource_with_upload[u'id'])

        assert resource_with_upload['url'] == expected_url

    def test_resource_download(self, app, resource_with_upload):
        u'''When trying to download resource
        from CKAN it should redirect to S3.'''

        user = factories.Sysadmin()
        env = {u'REMOTE_USER': six.ensure_str(user[u'name'])}

        response = app.get(
            url_for(
                u'dataset_resource.download',
                id=resource_with_upload[u'package_id'],
                resource_id=resource_with_upload[u'id'],
            ),
            extra_environ=env,
            follow_redirects=False
        )
        assert 302 == response.status_code

    def test_resource_download_not_found(self, app):
        u'''When trying to download resource from
        CKAN it should redirect to S3.'''

        user = factories.Sysadmin()
        env = {u'REMOTE_USER': six.ensure_str(user[u'name'])}

        response = app.get(
            url_for(
                u'dataset_resource.download',
                id=u'package_id',
                resource_id=u'resource_id',
            ),
            extra_environ=env,
            follow_redirects=False
        )
        assert 404 == response.status_code

    def test_resource_download_no_filename(self,
                                           app, resource_with_upload):
        '''A resource uploaded to S3 can be
        downloaded when no filename in
        url.'''
        resource_file_url = u'/dataset/{0}/resource/{1}/download' \
            .format(resource_with_upload[u'package_id'],
                    resource_with_upload[u'id'])

        response = app.get(resource_file_url,
                           follow_redirects=False)

        assert 302 == response.status_code

    def test_s3_download_link(self, app, s3_client, resource_with_upload):
        u'''A resource download from s3 test.'''

        user = factories.Sysadmin()
        env = {u'REMOTE_USER': six.ensure_str(user[u'name'])}

        response = app.get(
            url_for(
                u'dataset_resource.download',
                id=resource_with_upload[u'package_id'],
                resource_id=resource_with_upload[u'id'],
            ),
            extra_environ=env,
            follow_redirects=False
        )
        assert 302 == response.status_code
        assert response.location
        downloaded_file = requests.get(response.location)
        assert u'SnowCourseName, Number, Elev. metres,' \
               in downloaded_file.text

    def test_s3_resource_mimetype(self, resource_with_upload):
        u'''A resource mimetype test.'''

        assert u'text/csv' == resource_with_upload[u'mimetype']

    def test_organization_image_redirects_to_s3(self,
                                                app,
                                                organization_with_image):
        url = u'/uploads/group/{0}'\
            .format(organization_with_image[u'image_url'])
        response = app.get(url,
                           follow_redirects=False)
        assert 302 == response.status_code

    def test_organization_image_download_from_s3(self,
                                                 app,
                                                 organization_with_image):
        url = u'/uploads/group/{0}'\
            .format(organization_with_image[u'image_url'])
        response = app.get(url,
                           follow_redirects=False)
        assert 302 == response.status_code
        assert response.location
        image = requests.get(response.location)
        assert image.content == b"\0\0\0"
