# encoding: utf-8
import pytest

import ckan.tests.factories as factories

from ckanext.s3filestore.uploader import BaseS3Uploader


@pytest.fixture
def s3_session(ckan_config):
    base_uploader = BaseS3Uploader()
    return base_uploader.get_s3_session()


@pytest.fixture
def s3_resource(ckan_config, s3_session):
    base_uploader = BaseS3Uploader()
    return base_uploader.get_s3_resource()


@pytest.fixture
def s3_client(ckan_config, s3_session):
    base_uploader = BaseS3Uploader()
    return base_uploader.get_s3_client()


@pytest.fixture
def resource_with_upload(create_with_upload):
    content = u"""
            SnowCourseName, Number, Elev. metres, DateOfSurvey, Snow Depth cm,\
            WaterEquiv. mm, SurveyCode, % of Normal, Density %, SurveyPeriod, \
            Normal mm
            SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
            MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
            NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
            """
    resource = create_with_upload(
        content, u'test.csv',
        package_id=factories.Dataset()[u"id"]
    )
    return resource


@pytest.fixture
def organization_with_image(create_with_upload):
    user = factories.Sysadmin()
    context = {
        u"user": user["name"]
    }
    org = create_with_upload(
        b"\0\0\0", u"image.png",
        context=context,
        action=u"organization_create",
        upload_field_name=u"image_upload",
        name=u"test-org"
    )
    return org
