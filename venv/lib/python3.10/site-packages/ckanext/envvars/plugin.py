import logging
import os
import ckan.plugins as plugins
import ckantoolkit as toolkit


log = logging.getLogger(__name__)


class EnvvarsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    @staticmethod
    def _envvar_to_ini(key):
        '''Transforms an env var formatted key to ini formatting.'''
        # If the key starts with 'CKAN___' (3 underscores).
        if key.startswith('CKAN___'):
            key = key[7:]
        # Set it to lowercase
        key = key.lower()
        # Replace dunders with dots
        key = key.replace('__', '.')

        return key

    # IConfigurer

    def update_config(self, config):

        # get all vars beginning with 'CKAN'
        ckan_vars = ((k, v) for k, v in os.environ.items()
                     if k.startswith('CKAN'))

        # transform vars into ini settings format
        ckan_vars = ((self._envvar_to_ini(k), v) for k, v in ckan_vars)

        # override config settings with new values
        config.update(dict(ckan_vars))

        # CKAN >=2.10 normalizes config values
        if toolkit.check_ckan_version(min_version='2.10'):
            from ckan.common import config_declaration
            config_declaration.normalize(config)
