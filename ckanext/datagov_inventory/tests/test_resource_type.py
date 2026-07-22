import pytest
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory datastore')
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestResourceTypePersistence:

    def test_resource_type_api_persists(self):
        dataset = factories.Dataset()
        resource = helpers.call_action(
            'resource_create',
            package_id=dataset['id'],
            url='https://api.example.gov/data',
            name='Test API',
            resource_type='api'
        )
        assert resource['resource_type'] == 'api'

        updated = helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://api.example.gov/data',
            name='Test API',
            resource_type='api'
        )
        assert updated['resource_type'] == 'api'

    def test_resource_type_file_persists(self):
        dataset = factories.Dataset()
        resource = helpers.call_action(
            'resource_create',
            package_id=dataset['id'],
            url='https://example.gov/data.csv',
            name='Test File',
            resource_type='file'
        )
        assert resource['resource_type'] == 'file'

        updated = helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.gov/data.csv',
            name='Test File',
            resource_type='file'
        )
        assert updated['resource_type'] == 'file'

    def test_resource_type_empty_string_persists(self):
        dataset = factories.Dataset()
        resource = helpers.call_action(
            'resource_create',
            package_id=dataset['id'],
            url='https://example.gov/portal',
            name='Test Access URL',
            resource_type=''
        )
        assert resource['resource_type'] == ''

        updated = helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.gov/portal',
            name='Test Access URL',
            resource_type=''
        )
        assert updated['resource_type'] == ''

    def test_resource_type_change_from_api_to_empty_persists(self):
        dataset = factories.Dataset()
        resource = helpers.call_action(
            'resource_create',
            package_id=dataset['id'],
            url='https://api.example.gov/data',
            name='Test Resource',
            resource_type='api'
        )
        assert resource['resource_type'] == 'api'

        updated = helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://example.gov/portal',
            name='Test Resource',
            resource_type=''
        )
        assert updated['resource_type'] == ''

        refetched = helpers.call_action('resource_show', id=resource['id'])
        assert refetched['resource_type'] == ''

    def test_resource_type_change_from_file_to_api_persists(self):
        dataset = factories.Dataset()
        resource = helpers.call_action(
            'resource_create',
            package_id=dataset['id'],
            url='https://example.gov/data.csv',
            name='Test Resource',
            resource_type='file'
        )
        assert resource['resource_type'] == 'file'

        updated = helpers.call_action(
            'resource_update',
            id=resource['id'],
            url='https://api.example.gov/data',
            name='Test Resource',
            resource_type='api'
        )
        assert updated['resource_type'] == 'api'

        refetched = helpers.call_action('resource_show', id=resource['id'])
        assert refetched['resource_type'] == 'api'

    def test_resource_type_invalid_value_rejected(self):
        dataset = factories.Dataset()
        with pytest.raises(Exception):
            helpers.call_action(
                'resource_create',
                package_id=dataset['id'],
                url='https://example.gov/portal',
                name='Test Resource',
                resource_type='accessurl'
            )
