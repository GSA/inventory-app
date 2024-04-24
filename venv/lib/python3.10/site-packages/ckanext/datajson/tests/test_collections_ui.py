import logging
from . import mock_datajson_source
from ckan import model
import ckanext.harvest.model as harvest_model
from ckanext.datajson.harvester_datajson import DataJsonHarvester
from .factories import HarvestJobObj, HarvestSourceObj
try:
    from ckan.tests import helpers, factories
except ImportError:
    from ckan.new_tests import helpers, factories

log = logging.getLogger(__name__)


class TestCollectionUI(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        super(TestCollectionUI, cls).setup_class()
        cls.user = factories.Sysadmin()
        cls.extra_environ = {'REMOTE_USER': cls.user['name'].encode('ascii')}
        cls.mock_port = 8953
        mock_datajson_source.serve(cls.mock_port)

    @classmethod
    def setup(cls):
        # Start data json sources server we can test harvesting against it
        helpers.reset_db()
        harvest_model.setup()

    def test_collection_ui(self):
        """ check if the user interface show collection as we expect """

        self.app = self._get_test_app()

        # harvest data
        datasets = self.get_datasets_from_2_collection()
        parents_found = 0
        for dataset in datasets:
            dataset = model.Package.get(dataset.id)
            log.info('Dataset found {}:{}'.format(dataset.name, dataset.id))
            # check for parents
            is_collection = False
            # geodatagov roll-up extras
            log.info('extras: {}'.format(dataset.extras))
            for extra in list(dataset.extras.items()):
                if extra[0] == 'collection_metadata':
                    is_collection = True

            if is_collection:
                log.info('Parent found {}:{}'.format(dataset.name, dataset.id))
                parents_found += 1

                # open parent dataset ui
                parent_name = dataset.name
                collection_package_id = dataset.id
                url = '/dataset/{}'.format(parent_name)
                log.info('Goto URL {}'.format(url))

                # show children
                url = '/dataset?collection_package_id={}'.format(collection_package_id)
                log.info('Goto URL {}'.format(url))
                res_redirect = self.app.get(url)
                assert '2 datasets found' in res_redirect.body

        assert parents_found == 2

    def get_datasets_from_2_collection(self):
        url = 'http://127.0.0.1:%s/collection-2-parent-4-children.data.json' % self.mock_port
        self.run_gather(url=url)
        self.run_fetch()
        datasets = self.run_import()
        return datasets

    def run_gather(self, url):
        self.source = HarvestSourceObj(url=url)
        self.job = HarvestJobObj(source=self.source)

        self.harvester = DataJsonHarvester()

        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = self.harvester.gather_stage(self.job)
        log.info('job.gather_errors=%s', self.job.gather_errors)
        log.info('obj_ids=%s', obj_ids)
        if len(obj_ids) == 0:
            # nothing to see
            return

        self.harvest_objects = []
        for obj_id in obj_ids:
            harvest_object = harvest_model.HarvestObject.get(obj_id)
            log.info('ho guid=%s', harvest_object.guid)
            log.info('ho content=%s', harvest_object.content)
            self.harvest_objects.append(harvest_object)

        return obj_ids

    def run_fetch(self):
        # fetch stage

        for harvest_object in self.harvest_objects:
            log.info('FETCHING %s' % harvest_object.id)
            result = self.harvester.fetch_stage(harvest_object)

            log.info('ho errors=%s', harvest_object.errors)
            log.info('result 1=%s', result)
            if len(harvest_object.errors) > 0:
                self.errors = harvest_object.errors

    def run_import(self, objects=None):
        # import stage
        datasets = []

        # allow run just some objects
        if objects is None:
            # default is all objects in the right order
            objects = self.harvest_objects
        else:
            log.info('Import custom list {}'.format(objects))

        for harvest_object in objects:
            log.info('IMPORTING %s' % harvest_object.id)
            result = self.harvester.import_stage(harvest_object)

            log.info('ho errors 2=%s', harvest_object.errors)
            log.info('result 2=%s', result)

            if not result:
                log.error('Dataset not imported: {}. Errors: {}. Content: {}'.format(harvest_object.package_id,
                                                                                     harvest_object.errors,
                                                                                     harvest_object.content))

            if len(harvest_object.errors) > 0:
                self.errors = harvest_object.errors
                harvest_object.state = "ERROR"

            harvest_object.state = "COMPLETE"
            harvest_object.save()

            log.info('ho pkg id=%s', harvest_object.package_id)
            dataset = model.Package.get(harvest_object.package_id)
            if dataset:
                datasets.append(dataset)
                log.info('dataset name=%s', dataset.name)

        return datasets
