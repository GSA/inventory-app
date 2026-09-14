from datetime import datetime, timedelta

import click

import ckan.model as model
import ckan.plugins.toolkit as toolkit


DEFAULT_INACTIVITY_DAYS = 90


def _utcnow():
    return datetime.utcnow()


def _last_activity(user):
    timestamps = [
        timestamp
        for timestamp in (user.last_active, user.created)
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


@click.command('delete-inactive-users')
@click.option(
    '--days',
    default=DEFAULT_INACTIVITY_DAYS,
    show_default=True,
    type=click.IntRange(min=1),
    help='Delete users inactive for more than this number of days.',
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='List users that would be deleted without deleting them.',
)
def delete_inactive_users(days, dry_run):
    """Delete CKAN users whose last activity is older than the cutoff."""
    cutoff = _utcnow() - timedelta(days=days)
    users = _inactive_users(cutoff)
    action = 'Would delete' if dry_run else 'Deleting'

    for user in users:
        last_activity = _last_activity(user)
        source = (
            'last_active'
            if last_activity == user.last_active
            else 'created'
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
            toolkit.get_action('user_delete')(
                {
                    'ignore_auth': True,
                    'model': model,
                },
                {'id': user.id},
            )

    result = 'Would delete' if dry_run else 'Deleted'
    click.echo('{} {} inactive user(s).'.format(result, len(users)))
