import ckan.lib.mailer as mailer
from ckan.plugins.toolkit import config


TOUCHPOINTS_URL = (
    'https://touchpoints.app.cloud.gov/touchpoints/9145dd7e'
)


def _site_url():
    return config.get('ckan.site_url', 'https://inventory.data.gov/')


def _mail_user(user, subject, body):
    # check smtp.user is set, otherwise smtp is not configured.
    if not config.get('smtp.user'):
        raise mailer.MailerException('SMTP is not configured')
    return mailer.mail_user(user, subject, body)


def send_about_to_lock(user, days):
    _mail_user(
        user,
        'Your Inventory.data.gov account will be locked soon',
        'Hello,\n\n'
        'Your Inventory.data.gov account is scheduled to be locked in '
        '{} days because it has been inactive.\n\n'
        'To keep your account active, sign in at:\n{}\n\n'
        'Account: {}\n'
        'Email: {}\n\n'
        'Thank you,\n'
        'Inventory.data.gov'.format(
            days, _site_url(), user.name, user.email
        ),
    )


def send_locked(user):
    _mail_user(
        user,
        'Your Inventory.data.gov account has been locked',
        'Hello,\n\n'
        'Your Inventory.data.gov account has been locked because it was '
        'inactive.\n\n'
        'To request that your account be unlocked, please complete this '
        'form:\n{}\n\n'
        'Account: {}\n'
        'Email: {}\n\n'
        'Thank you,\n'
        'Inventory.data.gov'.format(
            TOUCHPOINTS_URL, user.name, user.email
        ),
    )


def send_unlocked(user):
    _mail_user(
        user,
        'Your Inventory.data.gov account has been reactivated',
        'Hello,\n\n'
        'Your Inventory.data.gov account has been reactivated. You can '
        'sign in again at:\n{}\n\n'
        'Account: {}\n'
        'Email: {}\n\n'
        'Thank you,\n'
        'Inventory.data.gov'.format(
            _site_url(), user.name, user.email
        ),
    )
