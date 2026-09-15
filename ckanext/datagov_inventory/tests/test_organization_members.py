"""Tests for Inventory organization member management."""

import re

import pytest

import ckan.model as model
import ckan.tests.factories as factories


@pytest.mark.ckan_config('ckan.plugins', 'datagov_inventory')
@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestOrganizationMembers:
    def test_separates_active_and_deleted_members(self, app):
        active_user = factories.User(
            name='active-member',
            fullname='Active Member',
        )
        deleted_user = factories.User(
            name='deleted-member',
            fullname='Deleted Member',
        )
        organization = factories.Organization(
            context={'user': active_user['name']},
            users=[
                {'name': deleted_user['name'], 'capacity': 'editor'},
            ],
        )
        sysadmin = factories.Sysadmin()

        deleted_user_obj = model.User.get(deleted_user['id'])
        deleted_user_obj.state = model.State.DELETED
        model.Session.commit()

        token = factories.APIToken(user=sysadmin['name'])
        response = app.get(
            '/organization/manage_members/{}'.format(organization['name']),
            headers={'Authorization': token['token']},
            status=200,
        )
        page = response.data.decode('utf-8')

        active_section = page.index('Active User')
        deleted_section = page.index('Deleted User')
        count = re.search(r'<h3 class="page-heading">\s*([^<]+)', page)
        assert count and count.group(1).strip() == '2 members'
        assert active_section < page.index('Active Member') < deleted_section
        assert deleted_section < page.index('Deleted Member')

    def test_omits_deleted_section_without_deleted_members(self, app):
        active_user = factories.User()
        organization = factories.Organization(
            context={'user': active_user['name']},
        )
        sysadmin = factories.Sysadmin()

        token = factories.APIToken(user=sysadmin['name'])
        response = app.get(
            '/organization/manage_members/{}'.format(organization['name']),
            headers={'Authorization': token['token']},
            status=200,
        )
        page = response.data.decode('utf-8')

        count = re.search(r'<h3 class="page-heading">\s*([^<]+)', page)
        assert count and count.group(1).strip() == '1 member'
        assert 'Active User' in page
        assert 'Deleted User' not in page
