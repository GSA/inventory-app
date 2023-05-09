FROM python:3.9

# CKAN Setup Variables
ENV APP_DIR=/srv/app
ENV SRC_DIR=/srv/app/src
ENV SRC_EXTENSIONS_DIR=/srv/app/src_extensions
ENV CKAN_INI=${APP_DIR}/ckan.ini
ENV PIP_SRC=${SRC_DIR}
ENV CKAN_STORAGE_PATH=/var/lib/ckan
RUN mkdir -p $CKAN_STORAGE_PATH $APP_DIR $SRC_EXTENSIONS_DIR


RUN apt-get update -y && \
  apt-get install -y vim zip netcat

ADD README.md setup.py ${APP_DIR}/
ADD ckanext ${APP_DIR}/ckanext
ADD requirements.txt requirements-dev.txt ${APP_DIR}/
RUN pip3 install --upgrade pip && \
  pip3 install -r ${APP_DIR}/requirements.txt --ignore-installed && \
  pip3 install -r ${APP_DIR}/requirements-dev.txt --ignore-installed && \
  pip3 install -e ${APP_DIR}/


# CKAN Setup Files
# Our production ckan.ini messes with local login
# (so we need to generate a new one)
COPY config/prerun.py ${APP_DIR}/
RUN ckan generate config ${CKAN_INI}
COPY config/who.ini ${APP_DIR}/
COPY config/login.sandbox.idp.xml ${APP_DIR}/saml2

# In order for dependencies to be managed, python
# needs to be mapped to python3
RUN ln -s /usr/bin/python3 /usr/bin/python
