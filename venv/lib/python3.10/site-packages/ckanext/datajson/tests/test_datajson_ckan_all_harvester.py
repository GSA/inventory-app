from datetime import datetime
import json
import logging

import pytest

import ckan.plugins as p
import ckanext.harvest.model as harvest_model
import ckanext.harvest.queue as queue
from . import mock_datajson_source
from ckan import model
from ckan.lib.munge import munge_title_to_name
from ckanext.datajson.harvester_datajson import DataJsonHarvester
from ckanext.datajson.exceptions import ParentNotHarvestedException
from .factories import HarvestJobObj, HarvestSourceObj
from mock import Mock, patch

try:
    from ckan.tests.helpers import reset_db
    from ckan.tests.factories import Organization, Sysadmin
except ImportError:
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests.factories import Organization, Sysadmin

log = logging.getLogger(__name__)


class TestDataJSONHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        cls.mock_port = 8961
        mock_datajson_source.serve(cls.mock_port)

    @classmethod
    def setup(cls):
        # Start data json sources server we can test harvesting against it
        reset_db()
        harvest_model.setup()
        cls.user = Sysadmin()
        cls.org = Organization()

    def run_gather(self, url, config_str='{}'):
        self.source = HarvestSourceObj(url=url, owner_org=self.org['id'], config=config_str)
        self.job = HarvestJobObj(source=self.source)

        self.harvester = DataJsonHarvester()

        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = self.harvester.gather_stage(self.job)
        log.error('job.gather_errors=%s', self.job.gather_errors)
        log.info('obj_ids=%s', obj_ids)

        self.harvest_objects = []

        if len(obj_ids) == 0:
            # nothing to see
            log.error("NO objects found")
            return

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

    def run_source(self, url, config_str='{}'):
        self.run_gather(url, config_str)
        self.run_fetch()
        datasets = self.run_import()

        return datasets

    def test_datajson_collection(self):
        """ harvest from a source with a parent in the second place
            We expect the gather stage to re-order to the forst place """
        url = 'http://127.0.0.1:%s/collection-1-parent-2-children.data.json' % self.mock_port
        obj_ids = self.run_gather(url=url)

        identifiers = []
        for obj_id in obj_ids:
            harvest_object = harvest_model.HarvestObject.get(obj_id)
            content = json.loads(harvest_object.content)
            identifiers.append(content['identifier'])

        # We always expect the parent to be the first on the list
        expected_obj_ids = ['OPM-ERround-0001', 'OPM-ERround-0001-AWOL', 'OPM-ERround-0001-Retire']
        assert expected_obj_ids == identifiers

    def test_harvesting_parent_child_collections(self):
        """ Test that parent are beeing harvested first.
            When we harvest a child the parent must exists
            data.json from: https://www.opm.gov/data.json """

        url = 'http://127.0.0.1:%s/collection-1-parent-2-children.data.json' % self.mock_port
        obj_ids = self.run_gather(url=url)

        assert len(obj_ids) == 3

        self.run_fetch()
        datasets = self.run_import()

        assert len(datasets) == 3
        titles = ['Linking Employee Relations and Retirement',
                  'Addressing AWOL',
                  'Employee Relations Roundtables']

        parent_counter = 0
        child_counter = 0

        for dataset in datasets:
            assert dataset.title in titles
            extras = self.fix_extras(list(dataset.extras.items()))

            is_parent = extras.get('collection_metadata', 'false').lower() == 'true'
            is_child = extras.get('collection_package_id', None) is not None

            log.info('Harvested dataset {} {} {}'.format(dataset.title, is_parent, is_child))

            if dataset.title == 'Employee Relations Roundtables':
                assert is_parent is True
                assert is_child is False
                parent_counter += 1
            else:
                assert is_child is True
                assert is_parent is False
                child_counter += 1

        assert child_counter == 2
        assert parent_counter == 1

    def test_datason_arm(self):
        url = 'http://127.0.0.1:%s/arm' % self.mock_port
        datasets = self.run_source(url=url)
        dataset = datasets[0]
        # assert first element on list
        expected_title = "NCEP GFS: vertical profiles of met quantities at standard pressures, at Barrow"
        assert dataset.title == expected_title
        tags = [tag.name for tag in dataset.get_tags()]
        assert munge_title_to_name("ORNL") in tags
        assert len(dataset.resources) == 1

    def test_datason_arm_reharvest(self):
        url = 'http://127.0.0.1:%s/arm' % self.mock_port
        datasets = self.run_source(url=url)

        # fake job status before final RUN command.
        context = {'model': model, 'user': self.user['name'], 'session': model.Session}
        self.job.status = u'Running'
        self.job.gather_finished = datetime.utcnow()
        self.job.save()
        # Mark harvest job as complete
        p.toolkit.get_action('harvest_jobs_run')(context, {'source_id': self.source.id})

        # Re-run job to check harvester gather/comparison to previous data logic
        datasets = self.run_source(url=url)
        # Assert no datasets were changed
        assert datasets == []

    def test_datason_usda(self):
        url = 'http://127.0.0.1:%s/usda' % self.mock_port
        datasets = self.run_source(url=url)
        dataset = datasets[0]
        expected_title = "Department of Agriculture Congressional Logs for Fiscal Year 2014"
        assert dataset.title == expected_title
        tags = [tag.name for tag in dataset.get_tags()]
        assert len(dataset.resources) == 1
        assert munge_title_to_name("Congressional Logs") in tags

    def test_source_returning_http_error(self):
        url = 'http://127.0.0.1:%s/404' % self.mock_port
        self.run_source(url)
        assert self.job.gather_errors[0].message == ("HTTPError getting json source: "
                                                     "404 Client Error: Not Found for url: %s.") % url
        assert self.job.gather_errors[1].message == ("Error loading json content:"
                                                     " not enough values to unpack"
                                                     " (expected 2, got 0).")

        url = 'http://127.0.0.1:%s/500' % self.mock_port
        self.run_source(url)
        assert self.job.gather_errors[0].message == ("HTTPError getting json source: 500 Server Error: "
                                                     "Internal Server Error for url: %s.") % url
        assert self.job.gather_errors[1].message == ("Error loading json content:"
                                                     " not enough values to unpack"
                                                     " (expected 2, got 0).")

    def test_source_returning_url_error(self):
        # URL failing SSL
        url = 'https://127.0.0.1:%s' % self.mock_port
        self.run_source(url)

        assert "ConnectionError getting json source: HTTPSConnectionPool" in self.job.gather_errors[0].message
        assert self.job.gather_errors[1].message == ("Error loading json content:"
                                                     " not enough values to unpack"
                                                     " (expected 2, got 0).")

    def test_json_decode_error(self):
        url = 'http://127.0.0.1:%s/text' % self.mock_port

        self.run_source(url)
        assert "JSONDecodeError loading json." in self.job.gather_errors[0].message
        assert self.job.gather_errors[1].message == ("Error loading json content:"
                                                     " not enough values to unpack"
                                                     " (expected 2, got 0).")

    def get_datasets_from_2_collection(self):
        url = 'http://127.0.0.1:%s/collection-2-parent-4-children.data.json' % self.mock_port
        obj_ids = self.run_gather(url=url)

        assert len(obj_ids) == 6

        self.run_fetch()
        datasets = self.run_import()
        assert len(datasets) == 6
        return datasets

    @patch('ckanext.harvest.logic.action.update.harvest_source_show')
    def test_new_job_created(self, mock_harvest_source_show):

        def ps(context, data):
            return {u'id': self.source.id,
                    u'title': self.source.title,
                    u'state': u'active',
                    u'type': u'harvest',
                    u'source_type': self.source.type,
                    u'name': u'test_source_0',
                    u'active': False,
                    u'url': self.source.url,
                    u'extras': []}

        mock_harvest_source_show.side_effect = ps

        datasets = self.get_datasets_from_2_collection()

        context = {'model': model, 'user': self.user['name'], 'session': model.Session}

        # fake job status before final RUN command.
        self.job.status = u'Running'
        self.job.gather_finished = datetime.utcnow()
        self.job.save()

        p.toolkit.get_action('harvest_jobs_run')(context, {'source_id': self.source.id})

        jobs = harvest_model.HarvestJob.filter(source=self.source).all()
        source_config = json.loads(self.source.config or '{}')  # NOQA F841

        assert len(jobs) == 1
        assert jobs[0].status == 'Finished'

        return datasets

    def test_parent_child_counts(self):
        """ Test count for parent and children """

        datasets = self.get_datasets_from_2_collection()

        parent_counter = 0
        child_counter = 0

        for dataset in datasets:
            extras = self.fix_extras(list(dataset.extras.items()))
            is_parent = extras.get('collection_metadata', 'false').lower() == 'true'
            parent_package_id = extras.get('collection_package_id', None)
            is_child = parent_package_id is not None

            if is_parent:
                parent_counter += 1
            elif is_child:
                child_counter += 1

        assert parent_counter == 2
        assert child_counter == 4

    def fix_extras(self, extras):
        """ fix extras rolled up at geodatagov """
        new_extras = {}
        for e in extras:
            k = e[0]
            v = e[1]
            if k == 'extras_rollup':
                extras_rollup_dict = json.loads(v)
                for rk, rv in list(extras_rollup_dict.items()):
                    new_extras[rk] = rv
            else:
                new_extras[e[0]] = e[1]

        return new_extras

    # TODO: Fix test with connection to redis
    def test_raise_child_error_and_retry(self):
        """ if a harvest job for a child fails because
            parent still not exists we need to ensure
            this job will be retried.
            This test emulate the case we harvest children first
            (e.g. if we have several active queues).
            Just for CKAN 2.8 env"""

        # start harvest process with gather to create harvest objects
        url = 'http://127.0.0.1:%s/collection-1-parent-2-children.data.json' % self.mock_port
        self.run_gather(url=url)
        assert len(self.harvest_objects) == 3

        # create a publisher to send this objects to the fetch queue
        publisher = queue.get_fetch_publisher()

        for ho in self.harvest_objects:
            ho = harvest_model.HarvestObject.get(ho.id)  # refresh
            ho_data = json.loads(ho.content)
            assert ho.state == 'WAITING'
            log.info('HO: {}\n\tCurrent: {}'.format(ho_data['identifier'], ho.current))
            assert ho.retry_times == 0
            publisher.send({'harvest_object_id': ho.id})
            log.info('Harvest object sent to the fetch queue {} as {}'.format(ho_data['identifier'], ho.id))

        publisher.close()

        # run fetch for elements in the wrong order (first a child, the a parent)

        class FakeMethod(object):
            ''' This is to act like the method returned by AMQP'''
            def __init__(self, message):
                self.delivery_tag = message

        # get the fetch
        consumer_fetch = queue.get_fetch_consumer()
        qname = queue.get_fetch_queue_name()

        # first a child and assert to get an error
        r2 = json.dumps({"harvest_object_id": self.harvest_objects[1].id})
        r0 = FakeMethod(r2)
        with pytest.raises(ParentNotHarvestedException):
            queue.fetch_callback(consumer_fetch, r0, None, r2)
        assert self.harvest_objects[1].retry_times == 1
        assert self.harvest_objects[1].state == "ERROR"

        # run the parent later, like in a different queue
        r2 = json.dumps({"harvest_object_id": self.harvest_objects[0].id})
        r0 = FakeMethod(r2)
        queue.fetch_callback(consumer_fetch, r0, None, r2)
        assert self.harvest_objects[0].retry_times == 1
        assert self.harvest_objects[0].state == "COMPLETE"

        # Check status on harvest objects
        # We expect one child with error, parent ok and second child still waiting
        for ho in self.harvest_objects:
            ho = harvest_model.HarvestObject.get(ho.id)  # refresh
            ho_data = json.loads(ho.content)
            idf = ho_data['identifier']
            log.info('\nHO2: {}\n\tState: {}\n\tCurrent: {}\n\tGathered {}'.format(idf, ho.state, ho.current, ho.gathered))
            if idf == 'OPM-ERround-0001':
                assert ho.state == 'COMPLETE'
            elif idf == 'OPM-ERround-0001-AWOL':
                assert ho.state == 'ERROR'
                ho_awol_id = ho.id
            elif idf == 'OPM-ERround-0001-Retire':
                assert ho.state == 'WAITING'
                ho_retire_id = ho.id
            else:
                raise Exception('Unexpected identifier: "{}"'.format(idf))

        # resubmit jobs and objects as harvest_jobs_run does
        # we expect the errored harvest object is in this queue
        queue.resubmit_jobs()
        queue.resubmit_objects()

        # iterate over the fetch consumer queue again and check pending harvest objects
        harvest_objects = []
        while True:
            method, header, body = consumer_fetch.basic_get(queue=qname)
            if body is None:
                break

            body_data = json.loads(body)
            ho_id = body_data.get('harvest_object_id', None)
            log.info('Adding ho_id {}'.format(ho_id))
            if ho_id is not None:
                ho = harvest_model.HarvestObject.get(ho_id)
                if ho is not None:
                    harvest_objects.append(ho)
                    content = json.loads(ho.content)
                    log.info('Harvest object found {}: {} '.format(content['identifier'], ho.state))
                else:
                    log.info('Harvest object not found {}'.format(ho_id))

        ho_ids = [ho.id for ho in harvest_objects]

        # Now, we expect the waiting child and the errored one to be in the fetch queue

        log.info('Searching wainting object "Retire ID"')
        assert ho_retire_id in ho_ids

        log.info('Searching errored object "Awol ID"')
        assert ho_awol_id in ho_ids

    @patch('ckanext.datajson.harvester_datajson.DataJsonHarvester.get_harvest_source_id')
    @patch('ckan.plugins.toolkit.get_action')
    def test_parent_not_harvested_exception(self, mock_get_action, mock_get_harvest_source_id):
        """ unit test for is_part_of_to_package_id function
            Test for 2 parents with the same identifier.
            Just one belongs to the right harvest source """

        results = {'count': 2,
                   'results': [{'id': 'pkg-1',
                                'name': 'dataset-1',
                                'extras': [{'key': 'identifier', 'value': 'custom-identifier'}]},
                               {'id': 'pkg-2',
                                'name': 'dataset-2',
                                'extras': [{'key': 'identifier', 'value': 'custom-identifier'}]}]}

        def get_action(action_name):
            if action_name == 'package_search':
                return lambda ctx, data: results
            elif action_name == 'get_site_user':
                return lambda ctx, data: {'name': 'default'}

        mock_get_action.side_effect = get_action
        mock_get_harvest_source_id.side_effect = lambda package_id: 'hsi-{}'.format(package_id)

        harvest_source = Mock()
        harvest_source.id = 'hsi-pkg-99'  # raise error, not found
        harvest_object = Mock()
        harvest_object.source = harvest_source

        harvester = DataJsonHarvester()
        with pytest.raises(ParentNotHarvestedException):
            harvester.is_part_of_to_package_id('custom-identifier', harvest_object)

        assert mock_get_action.called

    @patch('ckanext.datajson.harvester_datajson.DataJsonHarvester.get_harvest_source_id')
    @patch('ckan.plugins.toolkit.get_action')
    def test_is_part_of_to_package_id_one_result(self, mock_get_action, mock_get_harvest_source_id):
        """ unit test for is_part_of_to_package_id function """

        results = {'count': 1,
                   'results': [{'id': 'pkg-1',
                                'name': 'dataset-1',
                                'extras': [{'key': 'identifier', 'value': 'identifier'}]}]}

        def get_action(action_name):
            if action_name == 'package_search':
                return lambda ctx, data: results
            elif action_name == 'get_site_user':
                return lambda ctx, data: {'name': 'default'}

        mock_get_action.side_effect = get_action
        mock_get_harvest_source_id.side_effect = lambda package_id: 'hsi-{}'.format(package_id)

        harvest_source = Mock()
        harvest_source.id = 'hsi-pkg-1'
        harvest_object = Mock()
        harvest_object.source = harvest_source

        harvester = DataJsonHarvester()
        dataset = harvester.is_part_of_to_package_id('identifier', harvest_object)
        assert mock_get_action.called
        assert dataset['name'] == 'dataset-1'

    @patch('ckanext.datajson.harvester_datajson.DataJsonHarvester.get_harvest_source_id')
    @patch('ckan.plugins.toolkit.get_action')
    def test_is_part_of_to_package_id_two_result(self, mock_get_action, mock_get_harvest_source_id):
        """ unit test for is_part_of_to_package_id function
            Test for 2 parents with the same identifier.
            Just one belongs to the right harvest source """

        results = {'count': 2,
                   'results': [{'id': 'pkg-1',
                                'name': 'dataset-1',
                                'extras': [{'key': 'identifier', 'value': 'custom-identifier'}]},
                               {'id': 'pkg-2',
                                'name': 'dataset-2',
                                'extras': [{'key': 'identifier', 'value': 'custom-identifier'}]}]}

        def get_action(action_name):
            if action_name == 'package_search':
                return lambda ctx, data: results
            elif action_name == 'get_site_user':
                return lambda ctx, data: {'name': 'default'}

        mock_get_action.side_effect = get_action
        mock_get_harvest_source_id.side_effect = lambda package_id: 'hsi-{}'.format(package_id)

        harvest_source = Mock()
        harvest_source.id = 'hsi-pkg-2'
        harvest_object = Mock()
        harvest_object.source = harvest_source

        harvester = DataJsonHarvester()
        dataset = harvester.is_part_of_to_package_id('custom-identifier', harvest_object)
        assert mock_get_action.called
        assert dataset['name'] == 'dataset-2'

    @patch('ckan.plugins.toolkit.get_action')
    def test_is_part_of_to_package_id_fail_no_results(self, mock_get_action):
        """ unit test for is_part_of_to_package_id function """

        def get_action(action_name):
            if action_name == 'package_search':
                return lambda ctx, data: {'count': 0}
            elif action_name == 'get_site_user':
                return lambda ctx, data: {'name': 'default'}

        mock_get_action.side_effect = get_action

        harvester = DataJsonHarvester()
        with pytest.raises(ParentNotHarvestedException):
            harvester.is_part_of_to_package_id('identifier', None)

    def test_datajson_is_part_of_package_id(self):
        url = 'http://127.0.0.1:%s/collection-1-parent-2-children.data.json' % self.mock_port
        obj_ids = self.run_gather(url=url)
        self.run_fetch()
        self.run_import()

        for obj_id in obj_ids:
            harvest_object = harvest_model.HarvestObject.get(obj_id)
            content = json.loads(harvest_object.content)
            # get the dataset with this identifier only if is a parent in a collection
            if content['identifier'] == 'OPM-ERround-0001':
                dataset = self.harvester.is_part_of_to_package_id(content['identifier'], harvest_object)
                assert dataset['title'] == 'Employee Relations Roundtables'

            if content['identifier'] in ['OPM-ERround-0001-AWOL', 'OPM-ERround-0001-Retire']:
                with pytest.raises(ParentNotHarvestedException):
                    self.harvester.is_part_of_to_package_id(content['identifier'], harvest_object)

        with pytest.raises(ParentNotHarvestedException):
            self.harvester.is_part_of_to_package_id('bad identifier', harvest_object)

    def test_datajson_non_federal(self):
        """ validate we get the coinfig we sent """
        url = 'http://127.0.0.1:%s/ny' % self.mock_port
        config = '{"validator_schema": "non-federal", "private_datasets": "False", "default_groups": "local"}'
        self.run_source(url, config)

        source_config = self.harvester.load_config(self.source)
        # include default values (filers and default)
        expected_config = {'defaults': {},
                           'filters': {},
                           'validator_schema': 'non-federal',
                           'default_groups': 'local',
                           'private_datasets': 'False'}
        assert source_config == expected_config

    def test_harvesting_parent_child_2_collections(self):
        """ Test that we have the right parents in each case """

        datasets = self.get_datasets_from_2_collection()

        for dataset in datasets:
            extras = self.fix_extras(list(dataset.extras.items()))
            parent_package_id = extras.get('collection_package_id', None)

            if dataset.title == 'Addressing AWOL':
                parent = model.Package.get(parent_package_id)
                # HEREX parent is None
                assert parent.title == 'Employee Relations Roundtables'
            elif dataset.title == 'Addressing AWOL 2':
                parent = model.Package.get(parent_package_id)
                assert parent.title == 'Employee Relations Roundtables 2'

    def test_datajson_reserverd_word_as_title(self):
        url = 'http://127.0.0.1:%s/error-reserved-title' % self.mock_port
        self.run_source(url=url)
        errors = self.errors
        expected_error_stage = "Import"
        assert errors[0].stage == expected_error_stage
        expected_error_message = "title: Search. That name cannot be used."
        assert errors[0].message == expected_error_message

    def test_datajson_large_spatial(self):
        url = 'http://127.0.0.1:%s/error-large-spatial' % self.mock_port
        self.run_source(url=url)
        errors = self.errors
        expected_error_stage = "Import"
        assert errors[0].stage == expected_error_stage
        expected_error_message = "spatial: Maximum allowed size is 32766. Actual size is 309643."
        assert errors[0].message == expected_error_message

    def test_datajson_null_spatial(self):
        url = 'http://127.0.0.1:%s/null-spatial' % self.mock_port
        datasets = self.run_source(url=url)
        dataset = datasets[0]
        expected_title = "Sample Title NUll Spatial"
        assert dataset.title == expected_title

    def test_datajson_numerical_title(self):
        url = 'http://127.0.0.1:%s/numerical-title' % self.mock_port
        datasets = self.run_source(url=url)
        dataset = datasets[0]
        expected_title = "707"
        assert dataset.title == expected_title
