# encoding: utf-8
import os

import pytest

from botocore.exceptions import ClientError

from ckantoolkit import config
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

from ckanext.s3filestore.uploader import S3Uploader
from ckanext.s3filestore.uploader import S3ResourceUploader


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
class TestS3ResourceUpload(object):

    @classmethod
    def setup_class(cls):
        cls.bucket_name = config.get(u'ckanext.s3filestore.aws_bucket_name')

    def test_resource_upload(self,
                             s3_client,
                             resource_with_upload, ckan_config):
        u'''Test a basic resource file upload'''

        key = u'resources/{0}/test.csv' \
            .format(resource_with_upload[u'id'])

        assert s3_client.head_object(Bucket=self.bucket_name, Key=key)

    def test_resource_upload_then_clear(self,
                                        s3_client,
                                        resource_with_upload,
                                        ckan_config):
        u'''Test that clearing an upload removes the S3 key'''

        key = u'resources/{0}/test.csv' \
            .format(resource_with_upload[u'id'])

        # key must exist
        assert s3_client.head_object(Bucket=self.bucket_name, Key=key)

        context = {u'user': factories.Sysadmin()[u'name']}
        helpers.call_action(u'resource_update', context,
                            clear_upload=True,
                            id=resource_with_upload[u'id'])

        # key shouldn't exist, this raises ClientError
        with pytest.raises(ClientError) as e:
            s3_client.head_object(Bucket=self.bucket_name, Key=key)

        assert e.value.response[u'Error'][u'Code'] == u'404'

    def test_resource_uploader_get_path(self):
        u'''Uploader get_path returns as expected'''
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'],
                                      name=u'myfile.txt')

        uploader = S3ResourceUploader(resource)
        returned_path = uploader.get_path(resource[u'id'], resource[u'name'])
        assert returned_path == u'resources/{0}/{1}'.format(resource[u'id'],
                                                            resource[u'name'])

    def test_uploader_get_path(self):
        storage_path = S3Uploader.get_storage_path(u'group')
        assert 'storage/uploads/group' == storage_path

    def test_create_organization_with_image(self,
                                            s3_client,
                                            organization_with_image,
                                            ckan_config):
        user = factories.Sysadmin()
        context = {
            u"user": user["name"]
        }
        result = helpers.call_action(u'organization_show', context,
                                     id=organization_with_image[u'id'])

        storage_path = S3Uploader.get_storage_path(u'group')
        filepath = os.path.join(storage_path, result[u'image_url'])

        # key must exist
        assert s3_client.head_object(Bucket=self.bucket_name, Key=filepath)

    # Since there is a bug in CKAN in _group_or_org_update()
    # def test_create_organization_with_image_then_clear(self,
    #                                                    s3_client,
    #                                                    organization_with_image,
    #                                                    ckan_config):
    #     user = factories.Sysadmin()
    #     context = {
    #         u"user": user["name"]
    #     }
    #     result = helpers.call_action(u'organization_show', context,
    #                                  id=organization_with_image[u'id'])
    #
    #     storage_path = S3Uploader.get_storage_path(u'group')
    #     key = os.path.join(storage_path, result[u'image_url'])
    #
    #     # key must exist
    #     assert s3_client.head_object(Bucket=self.bucket_name, Key=key)
    #
    #     helpers.call_action(u'organization_update', context,
    #                         clear_upload=True,
    #                         id=organization_with_image[u'id'],
    #                         name=organization_with_image[u'name'])
    #
    #     # key shouldn't exist, this raises ClientError
    #     with pytest.raises(ClientError) as e:
    #         s3_client.head_object(Bucket=self.bucket_name, Key=key)
    #
    #     assert e.value.response[u'Error'][u'Code'] == u'404'

    def test_delete_resource_from_s3(self, s3_client,
                                     resource_with_upload):

        resource_id = resource_with_upload[u'id']

        key = u'resources/{0}/test.csv' \
            .format(resource_with_upload[u'id'])

        # key must exist
        assert s3_client.head_object(Bucket=self.bucket_name, Key=key)

        uploader = S3ResourceUploader(resource_with_upload)

        uploader.delete(resource_id, u'test.csv')

        # key shouldn't exist, this raises ClientError
        with pytest.raises(ClientError):
            s3_client.head_object(Bucket=self.bucket_name, Key=key)

    def test_delete_image_from_s3(self, s3_client,
                                  organization_with_image):

        uploader = S3Uploader(u'group')
        storage_path = S3Uploader.get_storage_path(u'group')
        key = os.path.join(storage_path, organization_with_image[u'image_url'])

        # key must exist
        assert s3_client.head_object(Bucket=self.bucket_name, Key=key)

        uploader.delete(organization_with_image[u'image_url'])

        # key shouldn't exist, this raises ClientError
        with pytest.raises(ClientError):
            s3_client.head_object(Bucket=self.bucket_name, Key=key)
