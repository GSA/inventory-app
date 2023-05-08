FROM openknowledge/ckan-dev:2.9
# Inherit from here: https://github.com/okfn/docker-ckan/blob/master/ckan-dev/2.9/Dockerfile
# And then from here: https://github.com/okfn/docker-ckan/blob/master/ckan-base/2.9/Dockerfile

ENV GIT_BRANCH=2.9
ENV CKAN_HOME /srv/app
ENV CKAN_CONFIG /app/config
ENV APP_DIR /app
ENV VENV /app/venv
# ENV CKAN_ENV docker

# TODO: Figure out if these things are necessary?
# add dependencies for cryptography and vim
# RUN apk add libressl-dev musl-dev libffi-dev xmlsec vim xmlsec-dev

# Install vim and zip
RUN apk add vim zip

ADD README.md setup.py ${APP_DIR}/
ADD ckanext ${APP_DIR}/ckanext
ADD requirements.txt requirements-dev.txt ${APP_DIR}/
RUN pip3 install virtualenv && \
  virtualenv $VENV && \
  ${VENV}/bin/pip3 install --ignore-installed -r ${APP_DIR}/requirements.txt && \
  ${VENV}/bin/pip3 install --ignore-installed -r ${APP_DIR}/requirements-dev.txt

# COPY docker-entrypoint.d/* /docker-entrypoint.d/

# What saml2 info do we need?
# COPY saml2 ${APP_DIR}/saml2

# COPY the ini test file to the container 
# COPY test-catalog-next.ini ${SRC_DIR}/ckan

# Not currently in use in development
COPY config/gunicorn.conf.py $CKAN_CONFIG/
COPY config/server_start.sh $CKAN_CONFIG/

# Custom prerun script for Solr 8
COPY config/GSA_prerun.py ${CKAN_HOME}/
