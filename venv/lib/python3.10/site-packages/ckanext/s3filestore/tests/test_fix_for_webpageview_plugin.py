# encoding: utf-8
import requests

import pytest
from ckan.lib.helpers import url_for

from ckan.tests import helpers, factories


@pytest.mark.usefixtures(u'clean_db', u'clean_index')
@pytest.mark.ckan_config("ckan.plugins", "webpage_view s3filestore")
@pytest.mark.ckan_config("ckan.views.default_views", "webpage_view")
def test_view_shown_for_url_type_upload(app, create_with_upload):

    dataset = factories.Dataset()
    context = {u'user': factories.Sysadmin()[u'name']}

    content = u"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>WebpageView</title>
                </head>
                <body>
                </body>
                </html>
               """
    resource = create_with_upload(
        content, u'test.html',
        package_id=dataset["id"]
    )

    resource_view = helpers.call_action(u'resource_view_list', context,
                                        id=resource[u'id'])[0]

    with pytest.raises(KeyError):
        assert resource_view[u'page_url']

    resource_view_src_url = url_for(
        u's3_resource.resource_download',
        id=dataset[u'name'],
        resource_id=resource[u'id']
    )

    url = url_for(
        u'resource.read', id=dataset[u'name'], resource_id=resource[u'id']
    )

    response = app.get(url)

    assert (u'/dataset/{0}/resource/{1}/download?preview=True'
            .format(dataset[u'id'], resource[u'id'])
            in response)

    resource_view_src = app.get(resource_view_src_url,
                                follow_redirects=False)

    assert resource_view_src.location
    r = requests.get(resource_view_src.location)

    assert u'<title>WebpageView</title>' in r.text
