import ckan.lib.mailer as mailer
from ckan.plugins.toolkit import config


TOUCHPOINTS_URL = (
    'https://touchpoints.app.cloud.gov/touchpoints/9145dd7e'
)


def _site_url():
    return config.get('ckan.site_url', 'https://inventory.data.gov/')


def send_about_to_lock(user, days):
    mailer.mail_user(
        user,
        'Inventory.data.gov account will lock',
        'Inventory.data.gov\n\n'
        'User Account will lock after {} days of non-use: {} {}\n\n'
        'Login to Inventory.data.gov at: {}'.format(
            days, user.name, user.email, _site_url()
        ),
    )


def send_locked(user):
    mailer.mail_user(
        user,
        'Inventory.data.gov account locked',
        'Inventory.data.gov\n\n'
        'User Account is locked: {} {}\n\n'
        'To Request unlock, please fill in this form: {}'.format(
            user.name, user.email, TOUCHPOINTS_URL
        ),
    )


def send_unlocked(user):
    mailer.mail_user(
        user,
        'Inventory.data.gov account unlocked',
        'Inventory.data.gov\n\n'
        'User Account is unlocked: {} {}\n\n'
        'Login to Inventory.data.gov at: {}'.format(
            user.name, user.email, _site_url()
        ),
    )
