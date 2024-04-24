from past.utils import old_div
from ckanext.datajson.harvester_base import DatasetHarvesterBase

import requests
import re
import datetime


class CmsDataNavigatorHarvester(DatasetHarvesterBase):
    '''
    A Harvester for the CMS Data Navigator catalog.
    '''

    HARVESTER_VERSION = "0.9al"  # increment to force an update even if nothing has changed

    def info(self):
        return {
            'name': 'cms-data-navigator',
            'title': 'CMS Data Navigator',
            'description': 'Harvests CMS Data Navigator-style catalogs.',
        }

    def load_remote_catalog(self, harvest_job):
        catalog = requests.get(harvest_job.source.url).json()
        for item in catalog:
            item["identifier"] = item["ID"]
            item["title"] = item["Name"].strip()
        return catalog

    def set_dataset_info(self, package, dataset, dataset_defaults):
        extra(package, "Agency", "Department of Health & Human Services")
        package["author"] = "Centers for Medicare & Medicaid Services"
        extra(package, "author_id", "http://healthdata.gov/id/agency/cms")
        extra(package, "Bureau Code", "009:38")
        package["title"] = dataset["Name"].strip()
        package["notes"] = dataset.get("Description")

        package["url"] = dataset.get("Address")

        dataset_hd = dataset["HealthData"]
        extra(package, "Date Released", parsedate(dataset_hd.get("DateReleased")))
        extra(package, "Date Updated", parsedate(dataset_hd.get("DateUpdated")))
        extra(package, "Agency Program URL", dataset_hd.get("AgencyProgramURL"))
        extra(package, "Subject Area 1", "Medicare")
        extra(package, "Unit of Analysis", dataset_hd.get("UnitOfAnalysis"))
        extra(package, "Data Dictionary", dataset_hd.get("DataDictionaryURL"))
        extra(package, "Coverage Period", dataset_hd.get("Coverage Period"))
        extra(package, "Collection Frequency", dataset_hd.get("Collection Frequency"))
        extra(package, "Geographic Scope", dataset_hd.get("GeographicScope"))
        # 'X or Y' syntax returns Y if X is either None or the empty string
        extra(package, "Contact Name", dataset_hd.get("GenericContactName", None) or dataset_hd.get("ContactName"))
        extra(package, "Contact Email", dataset_hd.get("GenericContactEmail", None) or dataset_hd.get("ContactEmail"))
        extra(package, "License Agreement", dataset_hd.get("DataLicenseAgreementURL"))

        from ckan.lib.munge import munge_title_to_name
        package["tags"] = [{"name": munge_title_to_name(t["Name"])} for t in dataset.get("Keywords", [])]


def extra(package, key, value):
    if not value:
        return
    package.setdefault("extras", []).append({"key": key, "value": value})


def parsedate(msdate):
    if not msdate:
        return None
    if msdate == "/Date(-62135575200000-0600)/":
        return None  # is this "zero"?
    m = re.match(r"/Date\((\d+)([+\-]\d\d\d\d)\)\/", msdate)
    try:
        if not m:
            raise Exception("Invalid format.")
        isodate = datetime.datetime.fromtimestamp(old_div(int(m.group(1)), 1000)).isoformat().replace("T", " ")
    except BaseException:
        print("Invalid date in CMS Data Navigator: %s" % (msdate))
        return None
    # We're ignoring the time zone offset because our HHS metadata format does not
    # support it, until we check on how Drupal indexing will handle it.
    return isodate
