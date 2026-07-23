import ckan.model as model
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import secrets
import string


def create_inventory_user(context, data_dict):
    """Create a new user with .gov email validation and auto-generated password."""
    toolkit.check_access('create_inventory_user', context, data_dict)

    name = data_dict.get('name', '').strip()
    email = data_dict.get('email', '').strip()

    if not name:
        raise logic.ValidationError({'name': ['Missing value']})

    if not email:
        raise logic.ValidationError({'email': ['Missing value']})

    if '@' not in email or '.' not in email.split('@')[-1]:
        raise logic.ValidationError({'email': ['Invalid email format']})

    if not email.lower().endswith('.gov'):
        raise logic.ValidationError(
            {'email': ['Email must be from a .gov domain']}
        )

    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(32))

    user_dict = {
        'name': name,
        'email': email,
        'password': password
    }

    try:
        user = toolkit.get_action('user_create')(context, user_dict)
    except logic.ValidationError as e:
        raise e

    return user


def reactivate_user(context, data_dict):
    """Reactivate a deleted user by changing their state to active."""
    toolkit.check_access('reactivate_user', context, data_dict)

    user_id = data_dict.get('id', '').strip()

    if not user_id:
        raise logic.ValidationError({'id': ['Missing value']})

    user_obj = model.User.get(user_id)

    if not user_obj:
        raise logic.NotFound('User not found')

    if user_obj.state == 'active':
        raise logic.ValidationError(
            {'id': ['User is already active']}
        )

    user_obj.state = 'active'
    model.Session.add(user_obj)
    model.Session.commit()

    user_dict = toolkit.get_action('user_show')(
        {'ignore_auth': True},
        {'id': user_obj.id}
    )

    return user_dict


@toolkit.side_effect_free
def user_org_roles(context, data_dict):
    """Return users with organization roles, grouped by catagories."""
    toolkit.check_access('user_org_roles', context, data_dict)

    org_roles_by_user = _org_roles_by_user()
    users = model.Session.query(model.User).filter(
        model.User.state.in_([model.State.ACTIVE, model.State.DELETED])
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
            'state': user.state,
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
    """Sort users by display category, then by username within each category.

    The category order is:
    1. active sysadmins
    2. active users with at least one organization role
    3. active users without organization roles
    4. deleted users
    """
    if user['state'] == model.State.DELETED:
        group = 3
    elif user['sysadmin']:
        group = 0
    elif user['organizations']:
        group = 1
    else:
        group = 2

    return (group, (user['name'] or '').lower())
