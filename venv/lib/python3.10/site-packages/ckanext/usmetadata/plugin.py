import collections
import re
from logging import getLogger

from ckan.common import json
import ckan.lib.base as base
import ckan.lib.navl.validators as ckan_validators
import ckan.logic as logic
import ckan.plugins as p
from ckan.plugins.toolkit import requires_ckan_version, c
from . import db_utils
from . import blueprint
from . import helper as local_helper

requires_ckan_version("2.9")


log = getLogger(__name__)


class CommonCoreMetadataFormPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):
    """
    This plugin adds fields for the metadata (known as the DCAT-US) defined at
    https://resources.data.gov/schemas/dcat-us/v1.1/
    """
    p.implements(p.ITemplateHelpers, inherit=False)
    p.implements(p.IConfigurer, inherit=False)
    p.implements(p.IDatasetForm, inherit=False)
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.interfaces.IPackageController, inherit=True)
    p.implements(p.interfaces.IOrganizationController, inherit=True)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_resource('fanstatic', 'usmetadata')
        p.toolkit.add_public_directory(config, 'public')

    def validate(self, context, data_dict, schema, action):
        """
        Disabling validation during:
            - cloning process
            - draft datasets (when 'publishing_status=Draft')

        :param context:
        :param data_dict:
        :param schema:
        :param action:
        :return:
        """
        if context.get(
            'cloning',
            False) or 'skip_validation' in data_dict.get(
            'title',
                ''):
            data_dict, errors = p.toolkit.navl_validate(
                data_dict, schema, context)
            return data_dict, None

        if data_dict.get('publishing_status', '') == 'Draft':
            data_dict, errors = p.toolkit.navl_validate(
                data_dict, schema, context)
            if 'That URL is already in use.' in errors.get('name', []):
                # Only return URL in use error
                return data_dict, {'name': errors.get('name', [])}
            return data_dict, None

        return None

    @classmethod
    def usmetadata_filter(cls, data=None, mask='~~'):
        for redact in re.findall(local_helper.REDACTION_STROKE_REGEX, data):
            data = data.replace(redact, mask)
        data = data.replace('[[/REDACTED]]', mask)
        # render our custom snippet
        return data

    @classmethod
    def resource_redacted_icon(cls, package, resource, field):
        redacted_key = 'redacted_' + field
        if 'extras' in package:
            extras = dict([(x['key'], x['value']) for x in package['extras']])
            if 'public_access_level' not in extras:
                return ''
            if extras['public_access_level'] not in ['non-public', 'restricted public']:
                return ''
            if redacted_key not in resource or not resource[redacted_key]:
                return ''
            return '<img src="/redacted_icon.png" class="redacted-icon" />'
        return ''

    @classmethod
    def redacted_icon(cls, package, field):
        redacted_key = 'redacted_' + field
        if 'common_core' in package and 'public_access_level' in package['common_core']:
            core = package['common_core']
            pal = core['public_access_level']
            if pal not in ['non-public', 'restricted public']:
                return ''
            if redacted_key not in core or not core[redacted_key]:
                return ''
            return '<img src="/redacted_icon.png" class="redacted-icon" />'
        elif 'extras' in package:
            extras = dict([(x['key'], x['value']) for x in package['extras']])
            if 'public_access_level' not in extras:
                return ''
            if extras['public_access_level'] not in ['non-public', 'restricted public']:
                return ''
            if redacted_key not in extras or not extras[redacted_key]:
                return ''
            return '<img src="/redacted_icon.png" class="redacted-icon" />'
        return ''

    # Add access level facet on dataset page
    def dataset_facets(self, facets_dict, package_type):
        if package_type != 'dataset':
            return facets_dict
        d = collections.OrderedDict()
        d['public_access_level'] = 'Access Level'
        for k, vv in list(facets_dict.items()):
            d[k] = vv
        return d

    # Add access level facet on organization page
    def organization_facets(self, facets_dict, organization_type, package_type):
        if organization_type != 'organization':
            return facets_dict
        d = collections.OrderedDict()
        d['public_access_level'] = 'Access Level'
        for k, vv in list(facets_dict.items()):
            d[k] = vv
        return d

    def before_show(self, resource_dict):
        labels = collections.OrderedDict()
        labels["accessURL new"] = "Access URL"
        labels["conformsTo"] = "Conforms To"
        labels["describedBy"] = "Described By"
        labels["describedByType"] = "Described By Type"
        labels["format"] = "Media Type"
        labels["formatReadable"] = "Format"
        labels["created"] = "Created"

        resource_dict['labels'] = labels

        return resource_dict

    def edit(self, entity):
        # if dataset uses filestore to upload datafiles then make that dataset Public by default
        if hasattr(entity, 'type') and entity.type == u'dataset' and entity.private:
            for resource in entity.resources:
                if resource.url_type == u'upload':
                    entity.private = False
                    break
        return entity

    @classmethod
    def load_data_into_dict(cls, data_dict):
        '''
        a jinja2 template helper function.
        'extras' contains a list of dicts corresponding to the extras used to store arbitrary key value pairs in CKAN.
        This function moves each entry in 'extras' that is a DCAT-US metadata into 'common_core'

        Example:
        {'hi':'there', 'extras':[{'key': 'publisher', 'value':'USGS'}]}
        becomes
        {'hi':'there', 'common_core':{'publisher':'USGS'}, 'extras':[]}

        '''

        new_dict = data_dict.copy()
        common_metadata = [x['id'] for x in local_helper.required_metadata +  # NOQA
                           local_helper.required_if_applicable_metadata +  # NOQA
                           local_helper.expanded_metadata]

        try:
            new_dict['common_core']
        except KeyError:
            new_dict['common_core'] = {}

        reduced_extras = []
        parent_dataset_id = ""

        # Used to display user-friendly labels on dataset page
        dataset_labels = (
            ('name', 'Name'),
            ('title', 'Title'),
            ('notes', 'Description'),
            ('tag_string', 'Keywords (Tags)'),
            ('tags', 'Keywords (Tags)'),
            ('modified', 'Modified (Last Update)'),
            ('publisher', 'Publisher'),
            ('publisher_1', 'Sub-agency'),
            ('publisher_2', 'Sub-agency'),
            ('publisher_3', 'Sub-agency'),
            ('publisher_4', 'Sub-agency'),
            ('publisher_5', 'Sub-agency'),
            ('contact_name', 'Contact Name'),
            ('contact_email', 'Contact Email'),
            ('unique_id', 'Identifier'),
            ('public_access_level', 'Public Access Level'),
            ('bureau_code', 'Bureau Code'),
            ('program_code', 'Program Code'),
            ('access_level_comment', 'Rights'),
            ('license_id', 'License'),
            ('license_new', 'License'),
            ('spatial', 'Spatial'),
            ('temporal', 'Temporal'),
            ('category', 'Theme (Category)'),
            ('data_dictionary', 'Data Dictionary'),
            ('data_dictionary_type', 'Data Dictionary Type'),
            ('data_quality', 'Meets the agency Information Quality Guidelines'),
            ('publishing_status', 'Publishing Status'),
            ('accrual_periodicity', 'Accrual Periodicity (Frequency)'),
            ('conforms_to', 'Conforms To (Data Standard) '),
            ('homepage_url', 'Homepage Url'),
            ('language', 'Language'),
            ('primary_it_investment_uii', 'Primary IT Investment UII'),
            ('related_documents', 'Related Documents'),
            ('release_date', 'Release Date'),
            ('system_of_records', 'System of Records'),
            ('webservice', 'Webservice'),
            ('is_parent', 'Is parent dataset'),
            ('parent_dataset', 'Parent dataset'),
            ('accessURL', 'Download URL'),
            # ('accessURL_new', 'Access URL'),
            ('webService', 'Endpoint'),
            ('format', 'Media type'),
            ('formatReadable', 'Format')
        )

        new_dict['labels'] = collections.OrderedDict(dataset_labels)
        try:
            for extra in new_dict['extras']:
                # to take care of legacy On values for data_quality
                if extra['key'] == 'data_quality' and extra['value'] == 'on':
                    extra['value'] = "true"
                elif extra['key'] == 'data_quality' and extra['value'] == 'False':
                    extra['value'] = "false"

                if extra['key'] in common_metadata:
                    new_dict['common_core'][extra['key']] = extra['value']
                else:
                    reduced_extras.append(extra)

                # Check if parent dataset is present and if yes get details
                if extra['key'] == 'parent_dataset':
                    parent_dataset_id = extra['value']

            new_dict['extras'] = reduced_extras
        except KeyError as ex:
            log.debug('''Expected key ['%s'] not found, attempting to move DCAT-US keys to subdictionary''',
                      ex)
            # this can happen when a form fails validation, as all the data will now be as key,
            # value pairs, not under extras, so we'll move them to the expected point again to fill in the values
            # e.g.
            # { 'foo':'bar', 'publisher':'somename'} becomes {'foo':'bar', 'common_core':{'publisher':'somename'}}

            keys_to_remove = []

            # TODO remove debug
            log.debug('DCAT-US metadata: {0}'.format(common_metadata))
            for key, value in new_dict.items():
                # TODO remove debug
                log.debug('checking key: {0}'.format(key))
                if key in common_metadata:
                    # TODO remove debug
                    log.debug('adding key: {0}'.format(key))
                    new_dict['common_core'][key] = value
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del new_dict[key]

        # reorder keys
        new_dict['ordered_common_core'] = collections.OrderedDict()
        for key in new_dict['labels']:
            if key in new_dict['common_core']:
                new_dict['ordered_common_core'][key] = new_dict['common_core'][key]

        parent_dataset_options = db_utils.get_parent_organizations(c)

        # If parent dataset is set, Make sure dataset dropdown always has that value.
        if parent_dataset_id != "":
            parent_dataset_title = db_utils.get_organization_title(parent_dataset_id)

            if parent_dataset_id not in parent_dataset_options:
                parent_dataset_options[parent_dataset_id] = parent_dataset_title

        new_dict['parent_dataset_options'] = parent_dataset_options

        redacted = {}
        for exempt_field in local_helper.exempt_allowed:
            redacted_key = 'redacted_' + exempt_field
            if redacted_key in new_dict['common_core']:
                redacted[redacted_key] = new_dict['common_core'][redacted_key]
        new_dict['redacted_json'] = json.dumps(redacted)

        return new_dict

        # See ckan.plugins.interfaces.IDatasetForm

    def is_fallback(self):
        # Return True so that we use the extension's dataset form instead of CKAN's default for
        # /dataset/new and /dataset/edit
        return True

    # See ckan.plugins.interfaces.IDatasetForm
    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        #
        # return ['dataset', 'package']
        return []

    def _default_extras_schema(self):
        schema = {
            'id': [ckan_validators.ignore],
            'key': [ckan_validators.not_empty, local_helper.string],
            'value': [ckan_validators.not_missing],
            'state': [ckan_validators.ignore],
            'deleted': [ckan_validators.ignore_missing],
            'revision_timestamp': [ckan_validators.ignore],
            '__extras': [ckan_validators.ignore],
        }
        return schema

    # See ckan.plugins.interfaces.IDatasetForm
    def _create_package_schema(self, schema):
        log.debug("_create_package_schema called")
        try:
            base_path = base.request.path
            if base_path == u'/api/3/action/package_create':
                # This is called when the api is explicitly used
                for update in local_helper.schema_api_for_create:
                    schema.update(update)
            elif base_path == '/api/3/action/resource_create':
                for update in local_helper.schema_api_for_create:
                    schema.update(update)
        except RuntimeError:
            # This is called when 'factories.dataset' creates the dataset
            for update in local_helper.schema_updates_for_create:
                schema.update(update)

        # use convert_to_tags functions for taxonomy
        schema.update({
            'tag_string': [ckan_validators.not_empty,
                           p.toolkit.get_converter('convert_to_tags')],
            'extras': self._default_extras_schema()
            # 'resources': {
            # 'name': [ckan_validators.not_empty],
            # 'format': [ckan_validators.not_empty],
            # }
        })
        return schema

    def _modify_package_schema_update(self, schema):
        log.debug("_modify_package_schema_update called")
        for update in local_helper.schema_updates_for_update:
            schema.update(update)

        # use convert_to_tags functions for taxonomy
        schema.update({
            'tag_string': [ckan_validators.ignore_empty,
                           p.toolkit.get_converter('convert_to_tags')],
            'extras': self._default_extras_schema()
        })
        return schema

    def _modify_package_schema_show(self, schema):
        log.debug("_modify_package_schema_update_show called")
        for update in local_helper.schema_updates_for_show:
            schema.update(update)

        return schema

    # See ckan.plugins.interfaces.IDatasetForm
    def create_package_schema(self):
        # action, api, package_create
        # action=new and controller=package
        schema = super(CommonCoreMetadataFormPlugin, self).create_package_schema()
        schema = self._create_package_schema(schema)
        return schema

    # See ckan.plugins.interfaces.IDatasetForm
    def update_package_schema(self):
        log.debug('update_package_schema')

        # TODO: Figure out what to do with the 'action' and 'controller' code
        # find out action
        # action = base.request.environ['pylons.routes_dict']['action']
        # controller = base.request.environ['pylons.routes_dict']['controller']

        # TODO: This was already commented out when I looked at the coe
        # # if action == 'new_resource' and controller == 'package':
        # # schema = super(CommonCoreMetadataFormPlugin, self).update_package_schema()
        # # schema = self._create_resource_schema(schema)

        schema = super(CommonCoreMetadataFormPlugin, self).update_package_schema()
        schema = self._modify_package_schema_update(schema)

        # if action == 'edit' and controller == 'package':
        #     schema = self._create_package_schema(schema)
        # else:
        #     schema = self._modify_package_schema_update(schema)

        return schema

    # See ckan.plugins.interfaces.IDatasetForm
    def show_package_schema(self):
        log.debug('show_package_schema called')
        schema = super(CommonCoreMetadataFormPlugin, self).show_package_schema()

        # Don't show vocab tags mixed in with normal 'free' tags
        # (e.g. on dataset pages, or on the search page)
        schema['tags']['__extras'].append(p.toolkit.get_converter('free_tags_only'))

        # BELOW LINE MAY BE CAUSING SOLR INDEXING ISSUES.
        # schema = self._modify_package_schema_show(schema)

        return schema

    # Method below allows functions and other methods to be called from the Jinja template using the h variable
    # always_private hides Visibility selector, essentially meaning that all datasets are private to an organization
    def get_helpers(self):
        log.debug('get_helpers() called')
        return {
            'public_access_levels': local_helper.access_levels,
            'required_metadata': local_helper.required_metadata,
            'data_quality_options': local_helper.data_quality_options,
            'license_options': local_helper.license_options,
            'is_parent_options': local_helper.is_parent_options,
            'load_data_into_dict': self.load_data_into_dict,
            'accrual_periodicity': local_helper.accrual_periodicity,
            'publishing_status_options': local_helper.publishing_status_options,
            'always_private': True,
            'usmetadata_filter': self.usmetadata_filter,
            'redacted_icon': self.redacted_icon,
            'resource_redacted_icon': self.resource_redacted_icon,
            'get_action': logic.get_action
        }

    def get_blueprint(self):
        return blueprint.datapusher
