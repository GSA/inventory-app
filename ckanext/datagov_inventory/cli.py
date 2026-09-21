from datetime import datetime, timedelta
import logging

import click

import ckan.model as model
import ckan.plugins.toolkit as toolkit

from ckanext.datagov_inventory import user_activity
from ckanext.datagov_inventory import notifications


INACTIVITY_DAYS_CONFIG = (
    'ckanext.datagov_inventory.inactivity_days'
)
INACTIVITY_WARNING_DAYS_CONFIG = (
    'ckanext.datagov_inventory.inactivity_warning_days'
)
INACTIVITY_WARNING_DAYS_DEFAULT = 7

log = logging.getLogger(__name__)


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


def _inactivity_warning_days():
    value = toolkit.config.get(INACTIVITY_WARNING_DAYS_CONFIG)
    if value is None or value == '':
        value = INACTIVITY_WARNING_DAYS_DEFAULT
    try:
        days = int(value)
    except (TypeError, ValueError):
        raise click.ClickException(
            '{} must be a positive integer smaller than inactivity_days'
            .format(INACTIVITY_WARNING_DAYS_CONFIG)
        )

    if days < 1 or days >= _inactivity_days():
        raise click.ClickException(
            '{} must be a positive integer smaller than inactivity_days'
            .format(INACTIVITY_WARNING_DAYS_CONFIG)
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


def _about_to_lock_users(now, inactivity_days, warning_days):
    warning_cutoff = now - timedelta(days=inactivity_days - warning_days)
    users = model.Session.query(model.User).filter(
        model.User.state == model.State.ACTIVE
    ).order_by(model.User.name).all()

    return [
        user for user in users
        if (_last_activity(user) is not None
            and _last_activity(user) <= warning_cutoff)
        and user_activity.get_inactivity_warning_sent_at(user) is None
    ]


def _days_until_lock(user, now, inactivity_days):
    lock_at = _last_activity(user) + timedelta(days=inactivity_days)
    remaining = lock_at - now
    return max(1, (remaining.days + (remaining.seconds > 0)))


def _warning_is_old_enough(user, now, warning_days):
    warning_sent_at = user_activity.get_inactivity_warning_sent_at(user)
    return warning_sent_at is not None and warning_sent_at <= (
        now - timedelta(days=warning_days)
    )


def soft_delete(user):
    """Mark a user deleted without changing their memberships."""
    user.state = model.State.DELETED
    model.Session.add(user)
    model.Session.commit()
    try:
        notifications.send_locked(user)
    except Exception:
        log.exception('Unable to send locked notification for %s', user.name)


@click.command('delete-inactive-users')
@click.option(
    '--dry-run',
    is_flag=True,
    help='List users that would be deleted without deleting them.',
)
def delete_inactive_users(dry_run):
    """Delete CKAN users whose last activity is older than the cutoff."""
    days = _inactivity_days()
    warning_days = _inactivity_warning_days()
    now = _utcnow()
    cutoff = now - timedelta(days=days)
    warning_users = _about_to_lock_users(now, days, warning_days)
    for user in warning_users:
        remaining = (
            warning_days
            if _last_activity(user) < cutoff
            else _days_until_lock(user, now, days)
        )
        if dry_run:
            click.echo(
                'Would send warning email to {} ({}, {} days until lock)'
                .format(
                    user.name, user.email, remaining
                )
            )
        if not dry_run:
            try:
                notifications.send_about_to_lock(user, remaining)
            except Exception:
                log.exception(
                    'Unable to send about-to-lock notification for %s',
                    user.name,
                )
                click.echo(
                    'Warning email delivery failed for {}; continuing '
                    'as if it was sent.'.format(user.name)
                )
            else:
                click.echo(
                    'Sent warning email to {} ({}, {} days until lock)'
                    .format(user.name, user.email, remaining)
                )
            user_activity.set_inactivity_warning_sent_at(user, now)
            model.Session.add(user)
    if not dry_run:
        model.Session.commit()
    users = [
        user for user in _inactive_users(cutoff)
        if _warning_is_old_enough(user, now, warning_days)
    ]
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
