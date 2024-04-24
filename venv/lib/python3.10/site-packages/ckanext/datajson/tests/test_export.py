import json
import zipfile

import ckanext.harvest.model as harvest_model

from ckan.tests import factories

from ckan.tests.helpers import reset_db

from flask import Response
import ckan.config.middleware
from ckan.common import config
from ckan.tests.helpers import CKANTestApp, CKANTestClient


class CKANZipTestApp(CKANTestApp):
    ''' Special Test App to allow Zip Files '''
    def test_client(self, use_cookies=True):
        return CKANTestClient(self.app, Response, use_cookies=use_cookies)


class TestExport(object):

    @classmethod
    def setup(cls):
        # Start data json sources server we can test harvesting against it
        reset_db()
        harvest_model.setup()

    def create_datasets(self):

        self.user = factories.Sysadmin()
        self.user_name = self.user['name'].encode('ascii')
        self.organization = factories.Organization(name='myorg',
                                                   users=[{'name': self.user_name, 'capacity': 'Admin'}],
                                                   extras=[{'key': 'sub-agencies', 'value': 'sub-agency1,sub-agency2'}])
        self.subagency1 = factories.Organization(name='sub-agency1',
                                                 users=[{'name': self.user_name, 'capacity': 'Admin'}])
        self.subagency2 = factories.Organization(name='sub-agency2',
                                                 users=[{'name': self.user_name, 'capacity': 'Admin'}])

        dataset = {
            'public_access_level': 'public',
            'unique_id': '',
            'contact_name': 'Jhon',
            'program_code': '018:001',
            'bureau_code': '019:20',
            'contact_email': 'jhon@mail.com',
            'publisher': 'Publicher 01',
            'modified': '2019-01-27 11:41:21',
            'tag_string': 'tag01,tag02',
            'owner_org': self.organization['id'],
        }
        extra_for_draft = [{'key': 'publishing_status', 'value': 'Draft'}]
        d1 = dataset.copy()
        d1.update({'title': 'test 01 dataset', 'unique_id': 't1', 'extras': extra_for_draft})
        self.dataset1 = factories.Dataset(**d1)
        d2 = dataset.copy()
        d2.update({'title': 'test 02 dataset', 'unique_id': 't2'})
        self.dataset2 = factories.Dataset(**d2)
        d3 = dataset.copy()
        d3.update({'title': 'test 03 dataset', 'unique_id': 't3', 'extras': extra_for_draft})
        self.dataset3 = factories.Dataset(**d3)
        d4 = dataset.copy()
        d4.update({'title': 'test 04 dataset', 'unique_id': 't4'})
        self.dataset4 = factories.Dataset(**d4)
        d5 = dataset.copy()
        d5.update({'title': 'test 05 dataset', 'unique_id': 't5', 'owner_org': self.subagency1['id']})
        self.dataset5 = factories.Dataset(**d5)

    def test_draft_json(self):
        """ test /org-id/draft.json """

        # enable links (done in the INI file)
        # added this into test.ini
        # why this is not working
        # config['ckanext.datajson.inventory_links_enabled'] = "True"

        # create datasets
        self.create_datasets()

        config["ckan.legacy_templates"] = False
        config["testing"] = True
        app = ckan.config.middleware.make_app(config)
        self.app = CKANZipTestApp(app)
        url = '/organization/{}/draft.json'.format(self.organization['id'])
        extra_environ = {'REMOTE_USER': self.user_name}
        res = self.app.get(url, extra_environ=extra_environ)

        # zip file
        zip_path = '/tmp/test.zip'
        zf = open(zip_path, 'wb')
        zf.write(res.data)
        zf.close()
        zfile = zipfile.ZipFile(zip_path, 'r')
        for name in zfile.namelist():
            print('File Found {}'.format(name))
            zfile.extract(name)  # should create "draft_data.json"

        f = open('draft_data.json', 'r')
        raw = f.read()
        f.close()

        """ data sample
        {
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "describedBy": "https://project-open-data.cio.gov/v1.1/schema/catalog.json",
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "@type": "dcat:Catalog",
            "dataset": [
                {
                    "@type": "dcat:Dataset",
                    "title": "resource upload testing & publishing 3",
                    "description": "resource upload testing & publishing description",
                    "modified": "2020-10-28T16:25:10.772Z",
                    "accessLevel": "public",
                    "identifier": "xxx-0-01",
                    "license": "https://creativecommons.org/licenses/by/4.0/",
                    "rights": "true",
                    "publisher":
                        {"@type": "org:Organization", "name": "BOP - Bureau of Prisons"},
                    "contactPoint":
                        {"@type": "vcard:Contact", "fn": "joeq", "hasEmail": "mailto:joe@mail.com"},
                    "distribution": [
                        {"@type": "dcat:Distribution", "mediaType": "image/png", "title": "resource upload testing & publishing", "downloadURL": "https://inventory.sandbox.datagov.us/dataset/9fcc8e61-9f08-460a-a505-ca798076a9a9/resource/06b5522a-9abb-4f3e-a1ed-2d6ea5b0715f/download/2020-09-26.png"} # NOQA TODO Take this out if ever uncommented
                        ],
                    "keyword": ["tag"],
                    "bureauCode": ["015:11"],
                    "programCode": ["015:001"],
                    "language": ["en-US"]
                    }
                ]
        } """  # NOQA

        data_res = json.loads(raw)
        datasets = data_res['dataset']
        titles = [d['title'] for d in datasets]

        assert self.dataset2['title'] not in titles
        assert self.dataset4['title'] not in titles

        assert self.dataset1['title'] in titles
        assert self.dataset3['title'] in titles

    def test_subagency_data_json(self):
        ''' Test for https://github.com/GSA/datagov-deploy/issues/3365 '''

        # create datasets
        self.create_datasets()

        config["ckan.legacy_templates"] = False
        config["testing"] = True
        app = ckan.config.middleware.make_app(config)
        self.app = CKANZipTestApp(app)
        url = '/organization/{}/data.json'.format(self.organization['id'])
        extra_environ = {'REMOTE_USER': self.user_name}
        res = self.app.get(url, extra_environ=extra_environ)

        data_json = json.loads(res.data)
        datasets = [data_json['dataset'][i]['title'] for i in range(0, 5)]

        assert self.dataset1['title'] in datasets
        assert self.dataset2['title'] in datasets
        assert self.dataset3['title'] in datasets
        assert self.dataset4['title'] in datasets
        assert self.dataset5['title'] in datasets
