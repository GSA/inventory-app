from datetime import datetime

import pytest

from ckanext.datagov_inventory import plugin as plugin_module


@pytest.fixture
def plugin():
    return plugin_module.Datagov_IauthfunctionsPlugin()


@pytest.mark.parametrize(
    'hook_name',
    ['after_resource_create', 'after_resource_update']
)
def test_resource_save_touches_parent_dataset(
        monkeypatch, plugin, hook_name):
    # resource creation and updates should use the same parent-touch behavior.
    touched = []
    monkeypatch.setattr(
        plugin_module,
        '_touch_dataset_modified',
        lambda context, package_id: touched.append((context, package_id))
    )
    context = {'user': 'editor'}

    getattr(plugin, hook_name)(
        context,
        {'id': 'resource-id', 'package_id': 'dataset-id'}
    )

    assert touched == [(context, 'dataset-id')]


def test_resource_delete_touches_parent_when_no_resources_remain(
        monkeypatch, plugin):
    # package id must survive deletion when the remaining list is empty.
    touched = []
    monkeypatch.setattr(
        plugin_module,
        '_touch_dataset_modified',
        lambda context, package_id: touched.append((context, package_id))
    )
    context = {'user': 'editor'}

    plugin.before_resource_delete(
        context,
        {'id': 'resource-id'},
        [{'id': 'resource-id', 'package_id': 'dataset-id'}]
    )
    plugin.after_resource_delete(context, [])

    assert touched == [(context, 'dataset-id')]
    assert 'datagov_inventory_package_id' not in context


def test_touch_dataset_modified_uses_utc_iso_timestamp(monkeypatch):
    # data.json exports this custom modified field, so keep its ISO UTC format.
    calls = []

    def get_action(name):
        assert name == 'package_patch'

        def action(context, data_dict):
            calls.append((context, data_dict))

        return action

    monkeypatch.setattr(plugin_module.toolkit, 'get_action', get_action)
    context = {'user': 'editor'}

    plugin_module._touch_dataset_modified(context, 'dataset-id')

    assert calls[0][0] is context
    assert calls[0][1]['id'] == 'dataset-id'
    modified = calls[0][1]['modified']
    assert modified.endswith('Z')
    assert datetime.fromisoformat(modified.replace('Z', '+00:00')).tzinfo
