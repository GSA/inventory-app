# gunicorn prior to version 20.1.0 discloses "server" header
# https://github.com/GSA/datagov-deploy/issues/2826
import gunicorn
gunicorn.SERVER_SOFTWARE = ''
