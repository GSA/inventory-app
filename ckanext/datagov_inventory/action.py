import ckan.model as model
import ckan.plugins.toolkit as toolkit


@toolkit.side_effect_free
def user_org_roles(context, data_dict):
    """Return active users with organization roles, grouped by priority."""
    toolkit.check_access('user_org_roles', context, data_dict)

    org_roles_by_user = _org_roles_by_user()
    users = model.Session.query(model.User).filter(
        model.User.state == 'active'
    ).all()

    result = []
    for user in users:
        organizations = sorted(
            org_roles_by_user.get(user.id, []),
            key=lambda org: (org['name'] or '').lower()
        )
        result.append({
            'id': user.id,
            'name': user.name,
            'fullname': user.fullname,
            'email': user.email,
            'last_active': _format_datetime(user.last_active),
            'sysadmin': user.sysadmin,
            'organizations': organizations,
        })

    return sorted(result, key=_user_sort_key)


def _format_datetime(value):
    if not value:
        return ''
    return value.replace(microsecond=0).isoformat(sep=' ')


def _org_roles_by_user():
    """
    Retrieve a dictionary mapping user IDs to their roles within organizations.
    """
    org_roles_by_user = {}
    query = model.Session.query(model.Member, model.Group).join(
        model.Group,
        model.Member.group_id == model.Group.id
    ).filter(
        model.Member.table_name == 'user',
        model.Member.state == 'active',
        model.Group.state == 'active',
        model.Group.is_organization.is_(True),
    )

    for member, organization in query:
        org_roles_by_user.setdefault(member.table_id, []).append({
            'id': organization.id,
            'name': organization.name,
            'title': organization.title,
            'role': member.capacity,
        })

    return org_roles_by_user


def _user_sort_key(user):
    if user['sysadmin']:
        group = 0
    elif user['organizations']:
        group = 1
    else:
        group = 2

    return (group, (user['name'] or '').lower())
