FROM keitaro/base:0.4

MAINTAINER Keitaro Inc <info@keitaro.info>

ENV APP_DIR=/srv/app
ENV GIT_BRANCH 0.0.15
ENV GIT_URL https://github.com/ckan/datapusher.git
ENV JOB_CONFIG ${APP_DIR}/datapusher_settings.py

WORKDIR ${APP_DIR}

RUN apk add --no-cache python \
    py-pip \
    py-gunicorn \
    libffi-dev \
    libressl-dev \
    libxslt && \
    # Temporary packages to build CKAN requirements
    apk add --no-cache --virtual .build-deps \
    gcc \
    git \
    util-linux \
    musl-dev \
    python-dev \
    libxml2-dev \
    libxslt-dev 

# Fetch datapusher and install
RUN mkdir ${APP_DIR}/src && cd ${APP_DIR}/src && \
    git clone -b ${GIT_BRANCH} --depth=1 --single-branch ${GIT_URL} && \
    cd datapusher && \
    pip install -r requirements.txt && \
    python setup.py develop

COPY setup ${APP_DIR}

EXPOSE 8800
# --reload restats gunicoir when code changes
CMD ["gunicorn", "--reload", "--bind=0.0.0.0:8800", "--log-file=-", "wsgi"]