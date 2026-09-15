from datetime import datetime, timedelta

import click

import ckan.model as model
import ckan.plugins.toolkit as toolkit

from ckanext.datagov_inventory import user_activity


INACTIVITY_DAYS_CONFIG = (
    'ckanext.datagov_inventory.inactivity_days'
)


def _utcnow():
    return datetime.utcnow()


def _inactivity_days():
    value = toolkit.config.get(INACTIVITY_DAYS_CONFIG)
    try:
        days = int(value)
    except (TypeError, ValueError):
        raise click.ClickException(
            '{} must be a positive integer'.format(INACTIVITY_DAYS_CONFIG)
        )

    if days < 1:
        raise click.ClickException(
            '{} must be a positive integer'.format(INACTIVITY_DAYS_CONFIG)
        )

    return days


def _last_activity(user):
    try:
        reactivated_at = user_activity.get_reactivated_at(user)
    except (TypeError, ValueError):
        raise click.ClickException(
            'Invalid reactivated_at timestamp for user {}'.format(user.name)
        )

    timestamps = [
        timestamp
        for timestamp in (user.last_active, user.created, reactivated_at)
        if timestamp is not None
    ]
    return max(timestamps) if timestamps else None


def _inactive_users(cutoff):
    users = model.Session.query(model.User).filter(
        model.User.state == model.State.ACTIVE
    ).order_by(model.User.name).all()

    return [
        user for user in users
        if _last_activity(user) and _last_activity(user) < cutoff
    ]


def soft_delete(user):
    """Mark a user deleted without changing their memberships."""
    user.state = model.State.DELETED
    model.Session.add(user)
    model.Session.commit()


@click.command('delete-inactive-users')
@click.option(
    '--dry-run',
    is_flag=True,
    help='List users that would be deleted without deleting them.',
)
def delete_inactive_users(dry_run):
    """Delete CKAN users whose last activity is older than the cutoff."""
    days = _inactivity_days()
    cutoff = _utcnow() - timedelta(days=days)
    users = _inactive_users(cutoff)
    action = 'Would delete' if dry_run else 'Deleting'

    for user in users:
        last_activity = _last_activity(user)
        source = (
            'last_active'
            if last_activity == user.last_active
            else (
                'created'
                if last_activity == user.created
                else 'reactivated_at'
            )
        )
        click.echo(
            '{} {} ({}: {})'.format(
                action,
                user.name,
                source,
                last_activity.isoformat(),
            )
        )
        if not dry_run:
            soft_delete(user)

    result = 'Would delete' if dry_run else 'Deleted'
    click.echo('{} {} inactive user(s).'.format(result, len(users)))
