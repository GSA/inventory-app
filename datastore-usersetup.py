#!/usr/bin/python

# Connect to the $DATASTORE_URL and attempt to provision the read-only user

from __future__ import print_function
import os
import psycopg2
import re
import sys
from urllib.parse import urlparse


def squote(s):
    """
    Return s as a single-quoted quoted string
    """
    return u"'" + s.replace(u"'", u"''").replace(u'\0', '') + u"'"


def identifier(s):
    """
    Return s as a double-quoted string (good for psql identifiers)
    """
    return u'"' + s.replace(u'"', u'""').replace(u'\0', '') + u'"'


def hide_sensitive(s):
    """
    Return s with sensitive info replaced.
    """

    # Hide password with <...>
    s = re.sub(
            r'((?i)PASSWORD\s+)(\'.*?\')(\s*;\s*)',
            r'\g<1><...>\g<3>',
            s)

    return s


def datastore_sql(datastoredb, writeuser, readuser, readpassword):
    """
    Return some SQL to create and permission the datastore
    readonly user.
    """

    template_filename = 'set_permissions.sql'

    with open(template_filename) as fp:
        template = fp.read()

    return template.format(
        datastoredb=identifier(datastoredb),
        writeuser=identifier(writeuser),
        readuser=identifier(readuser),
        readpassword=squote(readpassword))


def get_env(name):
    if name not in os.environ:
        raise Exception("Required environment variable %s is missing" % name)
    value = os.environ[name]
    if not value:
        raise Exception("Environment variable %s missing value" % name)
    return value


def main():
    datastore_url = get_env('DATASTORE_URL')
    readuser = get_env('DS_RO_USER')
    readpassword = get_env('DS_RO_PASSWORD')

    datastore = urlparse(get_env('DATASTORE_URL'))
    datastoredb = datastore.path.lstrip('/')
    writeuser = datastore.username

    if not datastoredb:
        raise Exception("DATASTORE_URL is missing the database")
    if not writeuser:
        raise Exception("DATASTORE_URL is missing a user name")

    sql = datastore_sql(datastoredb, writeuser, readuser, readpassword)

    print("<datastore SQL>")
    print(hide_sensitive(sql))
    print("</datastore SQL>")

    try:
        with psycopg2.connect(datastore_url) as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
            except Exception as sql_e:
                print("Exception while executing SQL:", str(sql_e))
    except Exception as conn_e:
        print("Unable to connect to datastore:", str(conn_e))
        sys.exit(-1)


if __name__ == '__main__':
    main()
