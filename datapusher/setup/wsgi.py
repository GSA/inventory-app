import os
import sys

import ckanserviceprovider.web as web
web.init()

from datapusher import jobs

application = web.app
