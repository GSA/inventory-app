#!/usr/bin/python

# Connect to the $DATASTORE_URL and attempt to provision the read-only user

import os
import psycopg2
import sys

try:
    conn=psycopg2.connect(os.environ['DATASTORE_URL'])
except:
    print "Unable to connect to datastore"
    sys.exit(-1)

cur = conn.cursor()
try:
    cur.execute('CREATE USER ' + os.environ['DS_RO_USER'] + ' WITH NOCREATEUSER NOCREATEDB ENCRYPTED PASSWORD ' + os.environ['DS_RO_PASSWORD'])
    cur.execute(os.environ['DS_PERMS_SQL'])
except:
    print "Got exception setting up user; likely already exists"

