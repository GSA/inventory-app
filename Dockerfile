FROM ubuntu:14.04

ARG PYTHON_VERSION=2.7.10

ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_CONFIG /etc/ckan/
ENV CKAN_ENV docker

WORKDIR /opt/inventory-app

# Install required packages
RUN apt-get -q -y update
RUN apt-get -q -y install \
  curl \
  build-essential \
  git \
  libbz2-dev \
  libpq-dev \
  libssl-dev \
  libz-dev \
  swig \
  wget

# Download  python
RUN wget -O- https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz | tar -zxv -C /tmp

# Compile and install python
RUN cd /tmp/Python-$PYTHON_VERSION && \
  ./configure \
    --enable-ipv6 \
    --enable-shared \
    --enable-unicode=ucs4 \
    --with-ensurepip=install && \
  make && make install && \
  ldconfig

RUN /usr/local/bin/pip install -U pip && \
  /usr/local/bin/pip install virtualenv && \
  /usr/local/bin/pip install -U setuptools

# Create ckan virtualenv
RUN mkdir -p $CKAN_HOME && \
  virtualenv $CKAN_HOME -p /usr/local/bin/python

COPY requirements.txt /tmp/

# Install ckan dependencies
RUN $CKAN_HOME/bin/pip install -r /tmp/requirements.txt

COPY entrypoint-docker.sh /
ENTRYPOINT ["/entrypoint-docker.sh"]

CMD ["/bin/bash"]
