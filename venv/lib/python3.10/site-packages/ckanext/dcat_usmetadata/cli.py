import csv
import json

import ckan.plugins as p
from ckan import model

import click


def get_commands():
    return [dcat_usmetadata]


@click.group(u"dcat-usmetadata")
def dcat_usmetadata():
    """Does DCAT-US metadata setup.
    """
    pass


@dcat_usmetadata.command(u"import-publishers")
@click.argument(u"path_to_file")
def import_publishers(path_to_file):
    with open(path_to_file) as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # skip the headers
        data = list(reader)
        # Generate publishers extra for each CKAN org:
        for org in get_orgs_to_process(data):
            publishers_tree = []
            for row in data:
                if row[0] == org:
                    # Append the row but remove empty strings
                    publishers_tree.append([i for i in row if i])

            update_orgs_with_publishers(org, publishers_tree)


def get_orgs_to_process(rows):
    list_of_available_orgs = []
    for row in rows:
        list_of_available_orgs.append(row[0])
    unique_set_of_orgs = set(list_of_available_orgs)
    return list(unique_set_of_orgs)


def update_orgs_with_publishers(org, publishers_tree):
    # Update org metadata with the publishers data:
    try:
        user = p.toolkit.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        org_metadata = p.toolkit.get_action(
            'organization_show')({"user": user['name'], "ignore_auth": True}, {'id': org})
        org_extras = org_metadata.get('extras', [])
        index_of_publisher_extra = next(
            (i for i, item in enumerate(org_extras)
                if item['key'] == 'publisher'), None)
        if index_of_publisher_extra:
            org_extras[index_of_publisher_extra]['value'] = json.dumps(
                publishers_tree)
        else:
            org_extras.append(
                {'key': 'publisher', 'value': json.dumps(publishers_tree)})

        p.toolkit.get_action('organization_patch')(
            {"user": user['name'], "ignore_auth": True}, {'id': org, 'extras': org_extras})
        print("Updated publishers for '{}'".format(org))
    except Exception as e:
        print(e)
        print("Organization '{}' was not found".format(org))
