from datetime import datetime


PLUGIN_EXTRAS_NAMESPACE = 'datagov_inventory'
REACTIVATED_AT_KEY = 'reactivated_at'


def get_reactivated_at(user):
    plugin_extras = user.plugin_extras or {}
    inventory_extras = plugin_extras.get(PLUGIN_EXTRAS_NAMESPACE) or {}
    value = inventory_extras.get(REACTIVATED_AT_KEY)

    if value is None or isinstance(value, datetime):
        return value

    return datetime.fromisoformat(value)


def set_reactivated_at(user, reactivated_at):
    plugin_extras = dict(user.plugin_extras or {})
    inventory_extras = dict(
        plugin_extras.get(PLUGIN_EXTRAS_NAMESPACE) or {}
    )
    inventory_extras[REACTIVATED_AT_KEY] = reactivated_at.isoformat()
    plugin_extras[PLUGIN_EXTRAS_NAMESPACE] = inventory_extras
    user.plugin_extras = plugin_extras
