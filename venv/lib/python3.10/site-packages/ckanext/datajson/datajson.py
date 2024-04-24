from ckan import model
from ckan import plugins as p
from ckan.model import Session, Package
from ckan.logic import NotFound, get_action, ValidationError
from ckan.logic.validators import name_validator
import ckan.lib.dictization.model_dictize as model_dictize
from ckan.lib.munge import munge_title_to_name
from ckan.lib.navl.dictization_functions import Invalid, DataError
from ckan.lib.navl.validators import ignore_empty, unicode_only
from ckan.lib.search import rebuild

from ckanext.harvest.model import HarvestObject, HarvestObjectError, HarvestObjectExtra
from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.datajson.exceptions import ParentNotHarvestedException
import uuid
import hashlib
import json
import yaml
import os
import sansjson

from jsonschema.validators import Draft4Validator
from jsonschema import FormatChecker

from sqlalchemy.exc import IntegrityError
from sqlalchemy import case

import logging
log = logging.getLogger(__name__)

# watch out for these keys that their string values might go beyond Solr capacity
# https://github.com/GSA/datagov-deploy/issues/953
SIZE_CHECK_KEYS = ['spatial']
MAX_SIZE = 32766
VALIDATION_SCHEMA = [('', 'Project Open Data (Federal)'),
                     ('non-federal', 'Project Open Data (Non-Federal)'), ]


def validate_schema(schema):
    if schema not in [s[0] for s in VALIDATION_SCHEMA]:
        raise Invalid('Unknown validation schema: {0}'.format(schema))
    return schema


class DatasetHarvesterBase(HarvesterBase):
    '''
    A Harvester for datasets.
    '''
    _user_name = None

    # SUBCLASSES MUST IMPLEMENT
    # HARVESTER_VERSION = "1.0"
    # def info(self):
    #    return {
    #        'name': 'harvester_base',
    #        'title': 'Base Harvester',
    #        'description': 'Abstract base class for harvesters that pull in datasets.',
    #    }

    def validate_config(self, config):
        if not config:
            return config
        config_obj = yaml.safe_load(config)  # NOQA F841
        return config

    def load_config(self, harvest_source):
        # Load the harvest source's configuration data.

        ret = {
            "filters": {},  # map data.json field name to list of values one of which must be present
            "defaults": {},  # map field name to value to supply as default if none exists,
                             # handled by the actual importer module, so the field names may be arbitrary
        }

        if harvest_source.config is None or harvest_source.config == '':
            harvest_source.config = '{}'
        source_config = json.loads(harvest_source.config)
        log.debug('SOURCE CONFIG from DB {}'.format(source_config))
        ret.update(source_config)

        return ret

    def _get_user_name(self):
        if not self._user_name:
            user = p.toolkit.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
            self._user_name = user['name']

        return self._user_name

    def context(self):
        # Reusing the dict across calls to action methods can be dangerous, so
        # create a new dict every time we need it.
        # Setting validate to False is critical for getting the harvester plugin
        # to set extra fields on the package during indexing (see ckanext/harvest/plugin.py
        # line 99, https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/plugin.py#L99).
        return {"user": self._get_user_name(), "ignore_auth": True, "model": model}

    # SUBCLASSES MUST IMPLEMENT
    def load_remote_catalog(self, harvest_job):
        # Loads a remote data catalog. This function must return a JSON-able
        # list of dicts, each dict a dataset containing an 'identifier' field
        # with a locally unique identifier string and a 'title' field.
        raise Exception("Not implemented")

    def extra_schema(self):
        return {
            'validator_schema': [ignore_empty, unicode_only, validate_schema],
        }

    def gather_stage(self, harvest_job):
        # The gather stage scans a remote resource (like a /data.json file) for
        # a list of datasets to import.

        log.debug('In %s gather_stage (%s)' % (repr(self), harvest_job.source.url))

        # Start gathering.
        try:
            source_datasets, catalog_values = self.load_remote_catalog(harvest_job)
        except BaseException as e:
            self._save_gather_error("Error loading json content: %s." % (e), harvest_job)
            return []

        if len(source_datasets) == 0:
            return []

        DATAJSON_SCHEMA = {"https://project-open-data.cio.gov/v1.1/schema": '1.1', }

        # schema version is default 1.0, or a valid one (1.1, ...)
        schema_version = '1.0'
        parent_identifiers = set()
        child_identifiers = set()
        catalog_extras = {}
        if isinstance(catalog_values, dict):
            schema_value = catalog_values.get('conformsTo', '')
            if schema_value not in list(DATAJSON_SCHEMA.keys()):
                self._save_gather_error('Error reading json schema value.'
                                        ' The given value is %s.' % ('empty' if schema_value == ''
                                                                     else schema_value), harvest_job)
                return []
            schema_version = DATAJSON_SCHEMA.get(schema_value, '1.0')

            for dataset in source_datasets:
                parent_identifier = dataset.get('isPartOf')
                if parent_identifier:
                    parent_identifiers.add(parent_identifier)
                    child_identifiers.add(dataset.get('identifier'))

            # get a list of needed catalog values and put into hobj
            catalog_fields = ['@context', '@id', 'conformsTo', 'describedBy']
            catalog_extras = dict(('catalog_' + k, v)
                                  for (k, v) in catalog_values.items()
                                  if k in catalog_fields)

        # Loop through the packages we've already imported from this source
        # and go into their extra fields to get their source_identifier,
        # which corresponds to the remote catalog's 'identifier' field.
        # Make a mapping so we know how to update existing records.
        # Added: mark all existing parent datasets.
        # Added: order_by. In a clean system order_by is not needed. It
        # is needed when there are packages deleted by dedupe process, to
        # ensure the active pkg wins and assigns to existing_datasets[sid].
        existing_datasets = {}
        existing_parents = {}
        for hobj in model.Session.query(HarvestObject.package_id, Package)\
                .filter_by(source=harvest_job.source, current=True)\
                .join(Package, HarvestObject.package_id == Package.id)\
                .order_by(
                    case(
                        [
                            (Package.state == 'draft', 1),
                            (Package.state == 'deleted', 2),
                            (Package.state == 'active', 3),
                        ],
                        else_=0
                    ),
                    Package.metadata_created
        ):

            # Get the equivalent "package" dictionary as if package_show
            pkg = model_dictize.package_dictize(hobj[1], self.context())

            # TODO: Figure out why extras_rollup has everything, but extras doesn't
            sid = self.find_extra(pkg, "identifier")
            if sid is None:
                try:
                    sid = json.loads(self.find_extra(pkg, "extras_rollup")).get("identifier")
                except TypeError:
                    sid = None

            is_parent = self.find_extra(pkg, "collection_metadata")
            if is_parent is None:
                try:
                    is_parent = json.loads(self.find_extra(pkg, "extras_rollup")).get("collection_metadata")
                except TypeError:
                    is_parent = None

            if sid:
                existing_datasets[sid] = pkg
            if is_parent and pkg.get("state") == "active":
                existing_parents[sid] = pkg

        # which parent has been demoted to child level?
        existing_parents_demoted = set(
            identifier for identifier in list(existing_parents.keys())
            if identifier not in parent_identifiers)

        # which dataset has been promoted to parent level?
        existing_datasets_promoted = set(
            identifier for identifier in list(existing_datasets.keys())
            if identifier in parent_identifiers and identifier not in list(existing_parents.keys())
        )

        source = harvest_job.source
        source_config = self.load_config(source)

        if parent_identifiers:
            for parent in parent_identifiers & child_identifiers:
                self._save_gather_error("Collection identifier '%s' \
                    cannot be isPartOf another collection." % parent, harvest_job)

            new_parents = set(identifier for identifier in parent_identifiers  # NOQA F841
                              if identifier not in list(existing_parents.keys()))

        # Create HarvestObjects for any records in the remote catalog.

        object_ids = []
        seen_datasets = set()
        unique_datasets = set()

        filters = source_config["filters"]

        for dataset in source_datasets:
            # Create a new HarvestObject for this dataset and save the
            # dataset metdata inside it for later.

            # Check the config's filters to see if we should import this dataset.
            # For each filter, check that the value specified in the data.json file
            # is among the permitted values in the filter specification.
            matched_filters = True
            for k, v in list(filters.items()):
                if dataset.get(k) not in v:
                    matched_filters = False
            if not matched_filters:
                continue

            if 'identifier' not in dataset:
                self._save_gather_error("The property identifier is required", harvest_job)
                continue

            # Some source contains duplicate identifiers. skip all except the first one
            if dataset['identifier'] in unique_datasets:
                self._save_gather_error("Duplicate entry ignored for identifier: '%s'." % (dataset['identifier']), harvest_job)
                continue
            unique_datasets.add(dataset['identifier'])

            # Get the package_id of this resource if we've already imported
            # it into our system. Otherwise, assign a brand new GUID to the
            # HarvestObject. I'm not sure what the point is of that.

            log.info('Check existing dataset: {}'.format(dataset['identifier']))
            if dataset['identifier'] in existing_datasets:
                pkg = existing_datasets[dataset["identifier"]]
                pkg_id = pkg["id"]
                seen_datasets.add(dataset['identifier'])

                # We store a hash of the dict associated with this dataset
                # in the package so we can avoid updating datasets that
                # don't look like they've changed.
                source_hash = self.find_extra(pkg, "source_hash")

                if source_hash is None:
                    try:
                        source_hash = json.loads(self.find_extra(pkg, "extras_rollup")).get("source_hash")
                    except TypeError:
                        source_hash = None
                # use sha1 for existing hash created by older versions of function make_upstream_content_hash
                # use sha256 for any new hash
                # sha1 generates 40 characters, sha256 generates 64 characters
                sha1_or_sha256 = "sha1" if len(source_hash) == 40 else "sha256"

                if pkg.get("state") == "active" \
                        and dataset['identifier'] not in existing_parents_demoted \
                        and dataset['identifier'] not in existing_datasets_promoted \
                        and source_hash == self.make_upstream_content_hash(dataset,
                                                                           source,
                                                                           catalog_extras,
                                                                           schema_version,
                                                                           sha1_or_sha256):
                    log.info('{} Match. SKIP: {}'.format(sha1_or_sha256, dataset['identifier']))
                    continue
            else:
                pkg_id = uuid.uuid4().hex

            # Create a new HarvestObject and store in it the GUID of the
            # existing dataset (if it exists here already) and the dataset's
            # metadata from the remote catalog file.
            extras = [HarvestObjectExtra(
                key='schema_version', value=schema_version)]
            if dataset['identifier'] in parent_identifiers:
                extras.append(HarvestObjectExtra(
                    key='is_collection', value=True))
            elif dataset.get('isPartOf'):
                is_part_of = dataset.get('isPartOf')
                existing_parent = existing_parents.get(is_part_of, None)
                if existing_parent is None:  # maybe the parent is not harvested yet
                    parent_pkg_id = 'IPO:{}'.format(is_part_of)
                else:
                    parent_pkg_id = existing_parent['id']
                extras.append(HarvestObjectExtra(
                    key='collection_pkg_id', value=parent_pkg_id))
            for k, v in catalog_extras.items():
                extras.append(HarvestObjectExtra(key=k, value=v))

            log.info('Datajson creates a HO: {}'.format(dataset['identifier']))
            obj = HarvestObject(
                guid=pkg_id,
                job=harvest_job,
                extras=extras,
                content=json.dumps(dataset, sort_keys=True))    # use sort_keys to preserve field order so
            #                                                     hashes of this string are constant from run to run
            obj.save()

            # we are sorting parent datasets in the list first and then children so that the parents are
            # harvested first, we then use the parent id to associate the children to the parent
            if dataset['identifier'] in parent_identifiers:
                object_ids.insert(0, obj.id)
            else:
                object_ids.append(obj.id)

        # Remove packages no longer in the remote catalog.
        for upstreamid, pkg in list(existing_datasets.items()):
            if upstreamid in seen_datasets:
                continue  # was just updated
            if pkg.get("state") == "deleted":
                continue  # already deleted
            pkg["state"] = "deleted"
            log.warn('deleting package %s (%s) because it is no longer in %s' % (pkg["name"],
                                                                                 pkg["id"],
                                                                                 harvest_job.source.url))
            try:
                get_action('package_update')(self.context(), pkg)
                obj = HarvestObject(guid=pkg_id,
                                    package_id=pkg["id"],
                                    job=harvest_job, )
                obj.save()
                object_ids.append(obj.id)
            except ValidationError as e:
                self._save_gather_error('Error validating package: %s' % (e), harvest_job)

        return object_ids

    def fetch_stage(self, harvest_object):
        # Nothing to do in this stage because we captured complete
        # dataset metadata from the first request to the remote catalog file.
        return True

    # SUBCLASSES MUST IMPLEMENT
    def set_dataset_info(self, pkg, dataset, dataset_defaults, schema_version):
        # Sets package metadata on 'pkg' using the remote catalog's metadata
        # in 'dataset' and default values as configured in 'dataset_defaults'.
        raise Exception("Not implemented.")

    # validate dataset against POD schema
    # use a local copy.
    def _validate_dataset(self, validator_schema, schema_version, dataset):
        if validator_schema == 'non-federal':
            if schema_version == '1.1':
                file_path = 'pod_schema/non-federal-v1.1/dataset-non-federal.json'
            else:
                file_path = 'pod_schema/non-federal/single_entry.json'
        else:
            if schema_version == '1.1':
                file_path = 'pod_schema/federal-v1.1/dataset.json'
            else:
                file_path = 'pod_schema/single_entry.json'

        with open(os.path.join(
                os.path.dirname(__file__), file_path)) as json_file:
            schema = json.load(json_file)

        msg = ";"
        errors = Draft4Validator(schema, format_checker=FormatChecker()).iter_errors(dataset)
        count = 0
        for error in errors:
            count += 1
            msg = msg + " ### ERROR #" + str(count) + ": " + self._validate_readable_msg(error) + "; "
        msg = msg.strip("; ")
        if msg:
            id = "Identifier: " + (dataset.get("identifier") if dataset.get("identifier") else "Unknown")
            title = "Title: " + (dataset.get("title") if dataset.get("title") else "Unknown")
            msg = id + "; " + title + "; " + str(count) + " Error(s) Found. " + msg + "."
        return msg

    # make ValidationError readable.
    def _validate_readable_msg(self, e):
        msg = e.message
        # limit the message size to be 150 characters
        if len(msg) > 150:
            msg = msg[:100] + " ...[truncated]... " + msg[-50:]

        elem = ""
        try:
            if e.schema_path[0] == 'properties':
                elem = e.schema_path[1]
                elem = "'" + elem + "':"
        except Exception:
            pass

        return elem + msg

    def _size_check(self, key, value):
        if key in SIZE_CHECK_KEYS and value is not None and len(value) >= MAX_SIZE:
            raise DataError('%s: Maximum allowed size is %i. Actual size is %i.' % (
                key, MAX_SIZE, len(value)
            ))

    def get_harvest_source_id(self, package_id):
        harvest_object = model.Session.query(HarvestObject) \
            .filter(HarvestObject.package_id == package_id) \
            .filter(HarvestObject.current == True).first()  # NOQA If this is 'is' it doesn't work

        return harvest_object.source.id if harvest_object else None

    def is_part_of_to_package_id(self, ipo, harvest_object):
        """ Get an identifier from external source using isPartOf
            and returns the parent dataset or raises an ParentNotHarvestedException.
            Only search for datasets that are the parent of a collection.
            """
        ps = p.toolkit.get_action('package_search')
        query = 'extras_identifier:"{}" AND extras_collection_metadata:true'.format(ipo)
        try:
            results = ps(self.context(), {"fq": query})
        except BaseException as e:
            self._save_object_error(e, harvest_object, 'Import')
        log.info('Package search results {}'.format(results))

        if results['count'] > 0:  # event if we have only one we need to be sure is the parent I need
            # possible check identifier collision
            # check the URL of the source to validate
            datasets = results['results']
            harvest_source = harvest_object.source

            for dataset in datasets:
                extras = dataset.get('extras', [])
                identifiers = [extra['value'] for extra in extras if extra['key'] == 'identifier']
                if ipo not in identifiers:
                    log.error('BAD SEARCH for {}:{}'.format(ipo, identifiers))
                    continue

                dataset_harvest_source_id = self.get_harvest_source_id(dataset['id'])

                if harvest_source.id == dataset_harvest_source_id:
                    log.info('Parent dataset identified correctly')
                    return dataset
                else:
                    log.info('{} not found at {} for {}'.format(harvest_source.id, dataset_harvest_source_id, ipo))

        # we have 0 o bad results
        msg = 'Parent identifier not found: "{}"'.format(ipo)
        log.error(msg)
        try:
            harvest_object_error = HarvestObjectError(message=msg, object=harvest_object)
            harvest_object_error.save()
            harvest_object.state = "ERROR"
            harvest_object.save()
        except Exception:
            pass
        raise ParentNotHarvestedException('Unable to find parent dataset. Raising error to allow re-run later')

    def import_stage(self, harvest_object):
        # The import stage actually creates the dataset.

        log.debug('In %s import_stage' % repr(self))

        if harvest_object.content is None:
            return True

        dataset = json.loads(harvest_object.content)

        if 'title' not in dataset:
            self._save_object_error(f"Identifier {dataset['identifier']}: missing title field", harvest_object, 'Import')
            return None

        # Ensure title is a string for munging/manipulation
        # https://github.com/GSA/data.gov/issues/4172
        dataset['title'] = str(dataset['title'])
        schema_version = '1.0'  # default to '1.0'
        is_collection = False
        parent_pkg_id = ''
        catalog_extras = {}
        for extra in harvest_object.extras:
            if extra.key == 'schema_version':
                schema_version = extra.value
            if extra.key == 'is_collection' and extra.value:
                is_collection = True
            if extra.key == 'collection_pkg_id' and extra.value:
                parent_pkg_id = extra.value
                if parent_pkg_id.startswith('IPO:'):
                    # it's an IsPartOf ("identifier" at the external source)
                    log.info('IPO found {}'.format(parent_pkg_id))

                    #  check if parent is already harvested
                    parent_identifier = parent_pkg_id.replace('IPO:', '')
                    parent = self.is_part_of_to_package_id(parent_identifier, harvest_object)
                    parent_pkg_id = parent['id']

            if extra.key.startswith('catalog_'):
                catalog_extras[extra.key] = extra.value

            # if this dataset is part of collection, we need to check if
            # parent dataset exist or not. we dont support any hierarchy
            # in this, so the check does not apply to those of is_collection
            if parent_pkg_id and not is_collection:
                parent_pkg = None
                try:
                    parent_pkg = get_action('package_show')(self.context(),
                                                            {"id": parent_pkg_id})
                except Exception:
                    pass
                if not parent_pkg:
                    parent_check_message = "isPartOf identifer '%s' not found." \
                        % dataset.get('isPartOf')
                    self._save_object_error(parent_check_message, harvest_object,
                                            'Import')
                    return None

        # do title check here
        # https://github.com/GSA/datagov-deploy/issues/953
        title_to_check = self.make_package_name(dataset.get('title'), harvest_object.guid)
        try:
            name_validator(title_to_check, None)
        except Invalid as e:
            invalid_message = "title: %s. %s." % (dataset.get('title'), e.error)
            self._save_object_error(invalid_message, harvest_object, 'Import')
            return None

        # Get default values.
        source_config = self.load_config(harvest_object.source)
        dataset_defaults = source_config["defaults"]
        validator_schema = source_config.get('validator_schema')
        if schema_version == '1.0' and validator_schema != 'non-federal':
            lowercase_conversion = True
        else:
            lowercase_conversion = False

        MAPPING = {
            "title": "title",
            "description": "notes",
            "keyword": "tags",
            "modified": "extras__modified",  # ! revision_timestamp
            "publisher": "extras__publisher",  # !owner_org
            "contactPoint": "maintainer",
            "mbox": "maintainer_email",
            "identifier": "extras__identifier",  # !id
            "accessLevel": "extras__accessLevel",

            "bureauCode": "extras__bureauCode",
            "programCode": "extras__programCode",
            "accessLevelComment": "extras__accessLevelComment",
            "license": "extras__license",  # !license_id
            "spatial": "extras__spatial",  # Geometry not valid GeoJSON, not indexing
            "temporal": "extras__temporal",

            "theme": "extras__theme",
            "dataDictionary": "extras__dataDictionary",  # !data_dict
            "dataQuality": "extras__dataQuality",
            "accrualPeriodicity": "extras__accrualPeriodicity",
            "landingPage": "extras__landingPage",
            "language": "extras__language",
            "primaryITInvestmentUII": "extras__primaryITInvestmentUII",  # !PrimaryITInvestmentUII
            "references": "extras__references",
            "issued": "extras__issued",
            "systemOfRecords": "extras__systemOfRecords",

            "accessURL": None,
            "webService": None,
            "format": None,
            "distribution": None,
        }

        MAPPING_V1_1 = {
            "title": "title",
            "description": "notes",
            "keyword": "tags",
            "modified": "extras__modified",  # ! revision_timestamp
            "publisher": "extras__publisher",  # !owner_org
            "contactPoint": {"fn": "maintainer", "hasEmail": "maintainer_email"},
            "identifier": "extras__identifier",  # !id
            "accessLevel": "extras__accessLevel",

            "bureauCode": "extras__bureauCode",
            "programCode": "extras__programCode",
            "rights": "extras__rights",
            "license": "extras__license",  # !license_id
            "spatial": "extras__spatial",  # Geometry not valid GeoJSON, not indexing
            "temporal": "extras__temporal",

            "theme": "extras__theme",
            "dataDictionary": "extras__dataDictionary",  # !data_dict
            "dataQuality": "extras__dataQuality",
            "accrualPeriodicity": "extras__accrualPeriodicity",
            "landingPage": "extras__landingPage",
            "language": "extras__language",
            "primaryITInvestmentUII": "extras__primaryITInvestmentUII",  # !PrimaryITInvestmentUII
            "references": "extras__references",
            "issued": "extras__issued",
            "systemOfRecords": "extras__systemOfRecords",

            "distribution": None,
        }

        SKIP = ["accessURL", "webService", "format", "distribution"]  # will go into pkg["resources"]
        # also skip the processed_how key, it was added to indicate how we processed the dataset.
        SKIP.append("processed_how")

        SKIP_V1_1 = ["@type", "isPartOf", "distribution"]
        SKIP_V1_1.append("processed_how")

        if lowercase_conversion:

            mapping_processed = {}
            for k, v in list(MAPPING.items()):
                mapping_processed[k.lower()] = v

            skip_processed = [k.lower() for k in SKIP]

            dataset_processed = {'processed_how': ['lowercase']}
            for k, v in list(dataset.items()):
                if k.lower() in list(mapping_processed.keys()):
                    dataset_processed[k.lower()] = v
                else:
                    dataset_processed[k] = v

            if 'distribution' in dataset and dataset['distribution'] is not None:
                dataset_processed['distribution'] = []
                for d in dataset['distribution']:
                    d_lower = {}
                    for k, v in list(d.items()):
                        if k.lower() in list(mapping_processed.keys()):
                            d_lower[k.lower()] = v
                        else:
                            d_lower[k] = v
                dataset_processed['distribution'].append(d_lower)
        else:
            dataset_processed = dataset
            mapping_processed = MAPPING
            skip_processed = SKIP

        if schema_version == '1.1':
            mapping_processed = MAPPING_V1_1
            skip_processed = SKIP_V1_1

        validate_message = self._validate_dataset(validator_schema,
                                                  schema_version, dataset_processed)
        if validate_message:
            self._save_object_error(validate_message, harvest_object, 'Import')
            return None

        # We need to get the owner organization (if any) from the harvest
        # source dataset
        owner_org = None
        source_dataset = model.Package.get(harvest_object.source.id)
        if source_dataset.owner_org:
            owner_org = source_dataset.owner_org

        group_name = source_config.get('default_groups', '')

        # Assemble basic information about the dataset.

        pkg = {
            "state": "active",  # in case was previously deleted
            "owner_org": owner_org,
            "groups": [{"name": group_name}],
            "resources": [],
            "extras": [
                {
                    "key": "resource-type",
                    "value": "Dataset",
                },
                {
                    "key": "source_hash",
                    "value": self.make_upstream_content_hash(dataset, harvest_object.source, catalog_extras, schema_version),
                },
                {
                    "key": "source_datajson_identifier",
                    "value": True,
                },
                {
                    "key": "harvest_source_id",
                    "value": harvest_object.harvest_source_id,
                },
                {
                    "key": "harvest_object_id",
                    "value": harvest_object.id,
                },
                {
                    "key": "harvest_source_title",
                    "value": harvest_object.source.title,
                },
                {
                    "key": "source_schema_version",
                    "value": schema_version,
                },
            ]
        }

        extras = pkg["extras"]
        unmapped = []

        for key, value in dataset_processed.items():

            try:
                self._size_check(key, value)
            except DataError as e:
                self._save_object_error(e.error, harvest_object, 'Import')
                return None

            if key in skip_processed:
                continue
            new_key = mapping_processed.get(key)
            if not new_key:
                unmapped.append(key)
                continue

            # after schema 1.0+, we need to deal with multiple new_keys
            new_keys = []
            values = []
            if isinstance(new_key, dict):  # when schema is not 1.0
                _new_key_keys = list(new_key.keys())
                new_keys = list(new_key.values())
                values = []
                for _key in _new_key_keys:
                    values.append(value.get(_key))
            else:
                new_keys.append(new_key)
                values.append(value)

            if not any(item for item in values):
                continue

            mini_dataset = dict(list(zip(new_keys, values)))
            for mini_key, mini_value in mini_dataset.items():
                if not mini_value:
                    continue
                if mini_key.startswith('extras__'):
                    extras.append({"key": mini_key[8:], "value": mini_value})
                else:
                    pkg[mini_key] = mini_value

        # pick a fix number of unmapped entries and put into extra
        if unmapped:
            unmapped.sort()
            del unmapped[100:]
            for key in unmapped:
                value = dataset_processed.get(key, "")
                if value is not None:
                    extras.append({"key": key, "value": value})

        # if theme is geospatial/Geospatial, we tag it in metadata_type.
        themes = self.find_extra(pkg, "theme")
        if themes and ('geospatial' in [x.lower() for x in themes]):
            extras.append({'key': 'metadata_type', 'value': 'geospatial'})

        if is_collection:
            extras.append({'key': 'collection_metadata', 'value': 'true'})
        elif parent_pkg_id:
            extras.append(
                {'key': 'collection_package_id', 'value': parent_pkg_id}
            )

        for k, v in catalog_extras.items():
            extras.append({'key': k, 'value': v})

        # Set specific information about the dataset.
        self.set_dataset_info(pkg, dataset_processed, dataset_defaults, schema_version)

        # Try to update an existing package with the ID set in harvest_object.guid. If that GUID
        # corresponds with an existing package, get its current metadata.
        try:
            existing_pkg = get_action('package_show')(self.context(), {"id": harvest_object.guid})
        except NotFound:
            existing_pkg = None

        if existing_pkg:
            # Update the existing metadata with the new information.

            # But before doing that, try to avoid replacing existing resources with new resources
            # my assigning resource IDs where they match up.
            for res in pkg.get("resources", []):
                for existing_res in existing_pkg.get("resources", []):
                    if res["url"] == existing_res["url"]:
                        res["id"] = existing_res["id"]
            pkg['groups'] = existing_pkg['groups']
            existing_pkg.update(pkg)  # preserve other fields that we're not setting, but clobber extras
            pkg = existing_pkg

            log.warn('updating package %s (%s) from %s' % (pkg["name"], pkg["id"], harvest_object.source.url))
            try:
                pkg = get_action('package_update')(self.context(), pkg)
            except ValidationError as e:
                log.error('Failed to update package %s: %s' % (pkg["name"], str(e)))
                self._save_object_error('Error updating package: %s' % (e), harvest_object, 'Import')
                return None
        else:
            # It doesn't exist yet. Create a new one.
            pkg['name'] = self.make_package_name(dataset_processed["title"], harvest_object.guid)
            try:
                pkg = get_action('package_create')(self.context(), pkg)
                log.warn('created package %s (%s) from %s' % (pkg["name"], pkg["id"], harvest_object.source.url))
            except IntegrityError:
                # sometimes one fetch worker does not see new pkg added
                # by other workers. it gives db error for pkg with same title.
                model.Session.rollback()
                pkg['name'] = self.make_package_name(dataset_processed["title"], harvest_object.guid)
                pkg = get_action('package_create')(self.context(), pkg)
                log.warn('created package %s (%s) from %s' % (pkg["name"], pkg["id"], harvest_object.source.url))
            except ValidationError as e:
                log.error('Failed to create package %s: %s' % (pkg["name"], str(e)))
                self._save_object_error('Error creating package: %s' % (e), harvest_object, 'Import')
                return None
            except Exception as e:
                log.error('Failed to create package %s from %s\n\t%s\n\t%s' % (pkg["name"],
                                                                               harvest_object.source.url,
                                                                               str(pkg),
                                                                               str(e)))
                raise

        # Flag the other HarvestObjects linking to this package as not current anymore
        for ob in model.Session.query(HarvestObject).filter_by(package_id=pkg["id"]):
            ob.current = False
            ob.save()

        # Flag this HarvestObject as the current harvest object
        harvest_object.package_id = pkg['id']
        harvest_object.current = True
        harvest_object.save()
        model.Session.commit()

        # Now that the package and the harvest source are associated, re-index the
        # package so it knows it is part of the harvest source. The CKAN harvester
        # does this by creating the association before the package is saved by
        # overriding the GUID creation on a new package. That's too difficult.
        # So here we end up indexing twice.
        rebuild(pkg['id'])

        return True

    def make_upstream_content_hash(self, datasetdict, harvest_source,
                                   catalog_extras, schema_version='1.0',
                                   sha1_or_sha256='sha256'):
        # sansjson.sort was added to sort dataset for better change detection.
        # doing so we can avoid updating datasets that don't have meaningful changes. (i.e. keyword order)

        # by default sansjson.sort and sha256 are used. sha1 is used for existing datasets,
        # until the dataset is changed and the hash is updated to new sha256.
        if sha1_or_sha256 == 'sha1':
            hash_function = hashlib.sha1
        else:
            hash_function = hashlib.sha256
            datasetdict = sansjson.sort_pyobject(datasetdict)

        if schema_version == '1.0':
            return hash_function(json.dumps(datasetdict, sort_keys=True) +  # NOQA W504
                                 "|" + harvest_source.config + "|" +  # NOQA W504
                                 self.HARVESTER_VERSION).hexdigest()
        else:
            return hash_function((json.dumps(datasetdict, sort_keys=True) + "|" + json.dumps(catalog_extras,
                                 sort_keys=True)).encode('utf-8')).hexdigest()

    def find_extra(self, pkg, key):
        for extra in pkg["extras"]:
            if extra["key"] == key:
                return extra["value"]
        return None

    def make_package_name(self, title, exclude_existing_package):
        '''
        Creates a URL friendly name from a title

        If the name already exists, it will add some random characters at the end
        '''

        name = munge_title_to_name(title).replace('_', '-')
        while '--' in name:
            name = name.replace('--', '-')
        name = name[0:90]  # max length is 100

        # Is this slug already in use (and if we're updating a package, is it in
        # use by a different package?).
        pkg_obj = Session.query(Package).filter(Package.name == name).filter(Package.id != exclude_existing_package).first()
        if not pkg_obj:
            # The name is available, so use it. Note that if we're updating an
            # existing package we will be updating this package's URL, so incoming
            # links may break.
            return name

        if exclude_existing_package:
            # The name is not available, and we're updating a package. Chances
            # are the package's name already had some random string attached
            # to it last time. Prevent spurrious updates to the package's URL
            # (choosing new random text) by just reusing the existing package's
            # name.
            pkg_obj = Session.query(Package).filter(Package.id == exclude_existing_package).first()
            if pkg_obj:     # the package may not exist yet because we may be passed the desired
                #             package GUID before a new package is instantiated
                return pkg_obj.name

        # Append some random text to the URL. Hope that with five character
        # there will be no collsion.
        return name + "-" + str(uuid.uuid4())[:5]
