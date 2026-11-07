"""Validation for datasets created through the action API."""

import pytest
from flask import Flask

import ckan.logic as logic
from ckanext.datagov_inventory import action
from ckanext.datagov_inventory.plugin import Datagov_IauthfunctionsPlugin


@pytest.mark.parametrize('notes', [None, '', '   ', 123])
def test_api_package_create_rejects_missing_description(notes):
    app = Flask(__name__)
    calls = []

    def original_action(context, data_dict):
        calls.append(data_dict)

    with app.test_request_context('/api/3/action/package_create'):
        with pytest.raises(logic.ValidationError) as error:
            action.package_create(original_action, {}, {'notes': notes})

    assert error.value.error_dict == {'notes': ['Missing value']}
    assert calls == []


def test_api_package_create_rejects_omitted_description():
    app = Flask(__name__)

    with app.test_request_context('/api/3/action/package_create'):
        with pytest.raises(logic.ValidationError) as error:
            action.package_create(lambda context, data: None, {}, {})

    assert error.value.error_dict == {'notes': ['Missing value']}


def test_api_package_create_passes_valid_description_to_ckan():
    app = Flask(__name__)
    data = {'name': 'test1234', 'notes': 'Description'}

    def original_action(context, data_dict):
        assert data_dict is data
        return {'id': 'created-id'}

    with app.test_request_context('/api/3/action/package_create'):
        result = action.package_create(original_action, {}, data)

    assert result == {'id': 'created-id'}


def test_non_api_package_create_keeps_existing_draft_behavior():
    app = Flask(__name__)

    with app.test_request_context('/dataset/new'):
        result = action.package_create(
            lambda context, data: {'notes': data['notes']},
            {},
            {'notes': None},
        )

    assert result == {'notes': None}


def test_plugin_registers_package_create_validation():
    assert Datagov_IauthfunctionsPlugin().get_actions()['package_create'] \
        is action.package_create
