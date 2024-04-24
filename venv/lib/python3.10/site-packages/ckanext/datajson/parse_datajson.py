from ckan.lib.munge import munge_title_to_name

import re


def parse_datajson_entry(datajson, package, defaults, schema_version):
    # four fields need extra handling, which are
    # 1.tag, 2.license, 3.maintainer_email, 4.publisher_hierarchy,
    # 5.resources

    # 1. package["tags"]
    package["tags"] = [{"name": munge_title_to_name(t)} for t in
                       package.get("tags", "") if t.strip() != ""]

    # 2. package["license"]
    licenses = {
        'Creative Commons Attribution': 'cc-by',
        'Creative Commons Attribution Share-Alike': 'cc-by-sa',
        'Creative Commons CCZero': 'cc-zero',
        'Creative Commons Non-Commercial (Any)': 'cc-nc',
        'GNU Free Documentation License': 'gfdl',
        'License Not Specified': 'notspecified',
        'Open Data Commons Attribution License': 'odc-by',
        'Open Data Commons Open Database License (ODbL)': 'odc-odbl',
        'Open Data Commons Public Domain Dedication and License (PDDL)': 'odc-pddl',
        'Other (Attribution)': 'other-at',
        'Other (Non-Commercial)': 'other-nc',
        'Other (Not Open)': 'other-closed',
        'Other (Open)': 'other-open',
        'Other (Public Domain)': 'other-pd',
        'UK Open Government Licence (OGL)': 'uk-ogl',

        # add more to complete the list
        'U.S. Public Domain Works': 'us-pd',
        'www.usa.gov/publicdomain/label/1.0': 'us-pd',

        # url (without protocol and trailing slash ) can also be used as key
        'creativecommons.org/licenses/by/4.0': 'cc-by',
        'creativecommons.org/licenses/by-sa/4.0': 'cc-by-sa',
        'creativecommons.org/publicdomain/zero/1.0': 'cc-zero',
        'creativecommons.org/licenses/by-nc/4.0': 'cc-nc',
        'www.gnu.org/copyleft/fdl.html': 'gfdl',
        'opendatacommons.org/licenses/by/1-0': 'odc-by',
        'opendatacommons.org/licenses/odbl': 'odc-odbl',
        'opendatacommons.org/licenses/pddl': 'odc-pddl',
        'project-open-data.cio.gov/unknown-license/#v1-legacy/other-at': 'other-at',
        'project-open-data.cio.gov/unknown-license/#v1-legacy/other-nc': 'other-nc',
        'project-open-data.cio.gov/unknown-license/#v1-legacy/other-closed': 'other-closed',
        'project-open-data.cio.gov/unknown-license/#v1-legacy/other-open': 'other-open',
        'creativecommons.org/publicdomain/mark/1.0/other-pd': 'other-pd',
        'www.nationalarchives.gov.uk/doc/open-government-licence/version/3': 'uk-ogl'
    }

    license = datajson.get("license")
    if not license:
        package["license_id"] = licenses.get("License Not Specified", "")
    else:
        license = license.replace("http://", "")
        license = license.replace("https://", "")
        license = license.rstrip('/')
        package["license_id"] = licenses.get(license, "other-license-specified")

    # 3. package["maintainer_email"]
    if package.get("maintainer_email"):
        package["maintainer_email"] = \
            package.get("maintainer_email").replace("mailto:", "", 1)

    # 4. extras-publisher and extras-publisher_hierarchy
    if schema_version == '1.1':
        publisher = find_extra(package, "publisher", {})
        publisher_name = publisher.get("name", "")
        set_extra(package, "publisher", publisher_name)
        parent_publisher = publisher.get("subOrganizationOf", {})
        publisher_hierarchy = []
        while parent_publisher:
            parent_name = parent_publisher.get("name", "")
            parent_publisher = parent_publisher.get("subOrganizationOf", {})
            publisher_hierarchy.append(parent_name)
        if publisher_hierarchy:
            publisher_hierarchy.reverse()
            publisher_hierarchy.append(publisher_name)
            publisher_hierarchy = " > ".join(publisher_hierarchy)
            set_extra(package, "publisher_hierarchy", publisher_hierarchy)

    # 5. package["resources"]
    # if distribution is empty, assemble it with root level accessURL and format.
    # but firstly it can be an ill-formated dict.
    distribution = datajson.get("distribution", [])
    if isinstance(distribution, dict):
        distribution = [distribution]
    if not isinstance(distribution, list):
        distribution = []

    downloadurl_key = "downloadURL"
    acccessurl_key = "accessURL"
    webservice_key = "webService"
    if datajson.get("processed_how", []) and "lowercase" in datajson.get("processed_how", []):
        acccessurl_key = acccessurl_key.lower()
        webservice_key = webservice_key.lower()

    if not distribution:
        for url in (acccessurl_key, webservice_key):
            if datajson.get(url, "") and datajson.get(url, "").strip():
                d = {
                    url: datajson.get(url, ""),
                    "format": datajson.get("format", ""),
                    "mimetype": datajson.get("format", ""),
                }
                distribution.append(d)

    datajson["distribution"] = distribution

    for d in datajson.get("distribution", []):
        downloadurl_value = d.get(downloadurl_key).strip() if d.get(downloadurl_key) else ''
        accessurl_value = d.get(acccessurl_key).strip() if d.get(acccessurl_key) else ''
        webservice_value = d.get(webservice_key).strip() if d.get(webservice_key) else ''

        which_value = ((accessurl_value or webservice_value) if schema_version == '1.0'
                       else (downloadurl_value or accessurl_value))

        if which_value:
            r = {}
            r['url'] = which_value
            r['format'] = d.get("format", "") if schema_version == '1.0' else d.get("format", d.get("mediaType", ""))
            r['mimetype'] = d.get("format", "") if schema_version == '1.0' else d.get("mediaType", "")
            r['description'] = d.get('description', '')
            r['name'] = d.get('title', '')

            # after schema 1.1+, we have some extra fields for resource
            resource_extras = ['conformsTo', 'describedBy', 'describedByType']
            for resource_extra_key in resource_extras:
                resource_extra_value = d.get(resource_extra_key)
                if resource_extra_value:
                    r[resource_extra_key] = resource_extra_value

            # after schema 1.1+, include acccessurl if it is left over
            if downloadurl_value and accessurl_value:
                r['accessURL'] = accessurl_value

            package["resources"].append(r)


def extra(package, key, value):
    if not value:
        return
    package.setdefault("extras", []).append({"key": key, "value": value})


def find_extra(pkg, key, default):
    for extra in pkg["extras"]:
        if extra["key"] == key:
            ret = extra["value"]
            break
    else:
        ret = default

    return ret


def set_extra(pkg, key, value):
    for extra in pkg["extras"]:
        if extra["key"] == key:
            extra["value"] = value
            break
    else:
        pkg["extras"].append({"key": key, "value": value})


def normalize_format(format, raise_on_unknown=False):
    if format is None:
        return
    # Format should be a file extension. But sometimes Socrata outputs a MIME type.
    format = format.lower()
    m = re.match(r"((application|text)/(\S+))(; charset=.*)?", format)
    if m:
        if m.group(1) == "text/plain":
            return "Text"
        if m.group(1) == "application/zip":
            return "ZIP"
        if m.group(1) == "application/vnd.ms-excel":
            return "XLS"
        if m.group(1) == "application/x-msaccess":
            return "Access"
        if raise_on_unknown:
            raise ValueError()    # caught & ignored by caller
        return "Other"
    if format == "text":
        return "Text"
    if raise_on_unknown and "?" in format:
        raise ValueError()    # weird value we should try to filter out; exception is caught & ignored by caller
    return format.upper()    # hope it's one of our formats by converting to upprecase
