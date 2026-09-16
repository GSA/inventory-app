"""Shared pytest configuration for the Inventory extension tests."""

from ckan.lib import search


def _skip_solr_schema_check(schema_file=None):
    """Skip CKAN's startup probe because this suite does not require Solr."""
    return False


search.check_solr_schema_version = _skip_solr_schema_check
