
# CKAN Extension for Inventory-app

The datagov_inventory CKAN extension provides Data.gov customizations
for inventory.data.gov.

Requirements

This extension works with CKAN 2.8.

## Installation

This extension will be installed automatically with inventory-app.

To install this extension manually or in another CKAN environment:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/bin/activate

2. Install the ckanext-datagov_inventory Python package into your virtual environment::

     `pip install -e git+https://github.com/GSA/inventory-app.git@master#egg=ckanext_datagov_inventory&subdirectory=ckanext-datagov_inventory`

3. Add ``datagov_inventory`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/production.ini``).

   This extension should be put at the beginning of the plugin list so classes are
   not overridden by other extensions.

4. Restart CKAN


## Tests


To run the nose tests::

    `nosetests --ckan --with-pylons=docker_test.ini ckanext-datagov_inventory/ckanext/datagov_inventory/tests/*`