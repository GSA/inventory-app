from ckan.common import c
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.dcat_usmetadata.cli as cli
from logging import getLogger

from . import blueprint
from . import db_utils as utils

toolkit.requires_ckan_version("2.9")

log = getLogger(__name__)


class Dcat_UsmetadataPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IBlueprint)

    # IClick
    plugins.implements(plugins.IClick)

    def get_commands(self):
        return cli.get_commands()

    # IConfigurer
    def update_config(self, config):
        plugins.toolkit.add_template_directory(config, "templates")
        plugins.toolkit.add_resource("public/assets", "dcat_usmetadata")
        plugins.toolkit.add_resource("fanstatic", "dcat_usmetadata_styles")
        plugins.toolkit.add_public_directory(config, "public")

    # IActions
    def get_actions(self):
        def parent_dataset_options(context, data_dict):
            return utils.get_parent_organizations(c)

        return {
            "parent_dataset_options": parent_dataset_options,
        }

    def get_blueprint(self):
        return blueprint.dcat_usmetadata
