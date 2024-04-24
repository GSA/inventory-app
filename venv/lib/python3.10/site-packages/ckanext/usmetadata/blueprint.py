import cgi
import datetime
from flask import Blueprint
from flask import redirect
from flask.wrappers import Response as response
from logging import getLogger
import re
import requests

from ckan.common import _, json, g
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.plugins
import ckan.logic as logic
import ckan.model as model
from ckan.plugins.toolkit import c, config, request, requires_ckan_version
from ckanext.usmetadata import helper as local_helper


requires_ckan_version("2.9")

datapusher = Blueprint('usmetadata', __name__)
log = getLogger(__name__)

render = base.render
abort = base.abort

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key
lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin


URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https:// or ftp:// or ftps://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

IANA_MIME_REGEX = re.compile(r"^[-\w]+/[-\w]+(\.[-\w]+)*([+][-\w]+)?$")

TEMPORAL_REGEX_1 = re.compile(
    r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
    r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?(\/)([\+-]?\d{4}'
    r'(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|'
    r'(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

TEMPORAL_REGEX_2 = re.compile(
    r'^(R\d*\/)?([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\4([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])'
    r'(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)'
    r'([\.,]\d+(?!:))?)?(\18[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?(\/)'
    r'P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+(?:\.\d+)?H)?'
    r'(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?$'
)

TEMPORAL_REGEX_3 = re.compile(
    r'^(R\d*\/)?P(?:\d+(?:\.\d+)?Y)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?W)?(?:\d+(?:\.\d+)?D)?(?:T(?:\d+'
    r'(?:\.\d+)?H)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?)?\/([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])'
    r'(\4([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))'
    r'([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]\d+(?!:))?)?(\18[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])'
    r'([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

LANGUAGE_REGEX = re.compile(
    r'^(((([A-Za-z]{2,3}(-([A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})(-([A-Za-z]{4}))?'
    r'(-([A-Za-z]{2}|[0-9]{3}))?(-([A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(-([0-9A-WY-Za-wy-z](-[A-Za-z0-9]{2,8})+))*'
    r'(-(x(-[A-Za-z0-9]{1,8})+))?)|(x(-[A-Za-z0-9]{1,8})+)|'
    r'((en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo'
    r'|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|'
    r'(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang)))$'
)

PRIMARY_IT_INVESTMENT_UII_REGEX = re.compile(r"^[0-9]{3}-[0-9]{9}$")

ISSUED_REGEX = re.compile(
    r'^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?'
    r'|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]'
    r'\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)?([zZ]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$'
)

REDACTED_REGEX = re.compile(
    r'^(\[\[REDACTED).*?(\]\])$'
)


def get_package_type(self, id):
    """
    Copied from https://github.com/ckan/ckan/blob/2.8/ckan/controllers/package.py#L866-L874
    Probably depreciated code..

    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or 'dataset'
    return None


def setup_template_variables(context, data_dict, package_type=None):
    """
    Copied from https://github.com/ckan/ckan/blob/2.9/ckan/views/dataset.py#L51-L54
    Doesn't exist in CKAN 2.8, so I don't know what happened here..
    """
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def get_package_info_usmetadata(id, context, errors, error_summary):
    data = get_action('package_show')(context, {'id': id})
    data_dict = get_action('package_show')(context, {'id': id})
    data_dict['id'] = id
    data_dict['state'] = 'active'
    context['allow_state_change'] = True
    try:
        get_action('package_update')(context, data_dict)
    except ValidationError as e:
        errors = e.error_dict
        error_summary = e.error_summary
        # ## TODO: Find out where 'new_metadata' is defined
        # return new_metadata(id, data, errors, error_summary)
        return
    except NotAuthorized:
        abort(401, _('Unauthorized to update dataset'))
    redirect(h.url_for(controller='package',
                       action='read', id=id))
    errors = errors or {}
    error_summary = error_summary or {}
    return {'data': data, 'errors': errors, 'error_summary': error_summary, 'pkg_name': id}


def map_old_keys(error_summary):
    replace = {
        'Format': 'Media Type'
    }
    for old_key, new_key in list(replace.items()):
        if old_key in list(error_summary.keys()):
            error_summary[new_key] = error_summary[old_key]
            del error_summary[old_key]
    return error_summary


def resource_form(package_type):
    # backwards compatibility with plugins not inheriting from
    # DefaultDatasetPlugin and not implmenting resource_form
    plugin = lookup_package_plugin(package_type)
    if hasattr(plugin, 'resource_form'):
        result = plugin.resource_form()
        if result is not None:
            return result
    return lookup_package_plugin().resource_form()


def new_resource_usmetadata(id, data=None, errors=None, error_summary=None):
    ''' FIXME: This is a temporary action to allow styling of the
    forms. '''
    if request.method == 'POST' and not data:
        save_action = request.params.get('save')
        data = data or clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(request.POST))))
        # we don't want to include save as it is part of the form
        del data['save']
        resource_id = data['id']
        del data['id']

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj}

        # see if we have any data that we are trying to save
        data_provided = False
        for key, value in data.items():
            if ((value or isinstance(value, cgi.FieldStorage)) and key != 'resource_type'):
                data_provided = True
                break

        if not data_provided and save_action != "go-dataset-complete":
            if save_action == 'go-dataset':
                # go to final stage of adddataset
                redirect(h.url_for(controller='package',
                                   action='edit', id=id))
            # see if we have added any resources
            try:
                data_dict = get_action('package_show')(context, {'id': id})
            except NotAuthorized:
                abort(401, _('Unauthorized to update dataset'))
            except NotFound:
                abort(404,
                      _('The dataset {id} could not be found.').format(id=id))
            if str.lower(config.get('ckan.package.resource_required', 'true')) == 'true' and not len(
                    data_dict['resources']):
                # no data so keep on page
                msg = _('You must add at least one data resource')
                # On new templates do not use flash message
                if g.legacy_templates:
                    h.flash_error(msg)
                    redirect(h.url_for(controller='package',
                                       action='new_resource', id=id))
                else:
                    errors = {}
                    error_summary = {_('Error'): msg}
                    return new_resource_usmetadata(id, data, errors, error_summary)
            # we have a resource so let them add metadata
            # redirect(h.url_for(controller='package',
            # action='new_metadata', id=id))
            extra_vars = get_package_info_usmetadata(id, context, errors, error_summary)
            package_type = get_package_type(id)
            setup_template_variables(context, {}, package_type=package_type)
            return render('package/new_package_metadata.html', extra_vars=extra_vars)

        data['package_id'] = id
        try:
            if resource_id:
                data['id'] = resource_id
                get_action('resource_update')(context, data)
            else:
                get_action('resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            # error_summary = e.error_summary
            error_summary = map_old_keys(e.error_summary)
            # return new_resource(id, data, errors, error_summary)
            return new_resource_usmetadata(id, data, errors, error_summary)

        except NotAuthorized:
            abort(401, _('Unauthorized to create a resource'))
        except NotFound:
            abort(404, _('The dataset {id} could not be found.'
                         ).format(id=id))
        if save_action == 'go-metadata':
            # go to final stage of add dataset
            # redirect(h.url_for(controller='package',
            # action='new_metadata', id=id))
            # Github Issue # 129. Removing last stage of dataset creation.
            extra_vars = get_package_info_usmetadata(id, context, errors, error_summary)
            package_type = get_package_type(id)
            setup_template_variables(context, {}, package_type=package_type)
            return render('package/new_package_metadata.html', extra_vars=extra_vars)
        elif save_action == 'go-dataset':
            # go to first stage of add dataset
            redirect(h.url_for(controller='package',
                               action='edit', id=id))
        elif save_action == 'go-dataset-complete':
            # go to first stage of add dataset
            redirect(h.url_for(controller='package',
                               action='read', id=id))
        else:
            # add more resources
            redirect(h.url_for(controller='package',
                               action='new_resource', id=id))

    # get resources for sidebar
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
    try:
        pkg_dict = get_action('package_show')(context, {'id': id})
    except NotFound:
        abort(404, _('The dataset {id} could not be found.').format(id=id))
    try:
        check_access(
            'resource_create', context, {"package_id": pkg_dict["id"]})
    except NotAuthorized:
        abort(401, _('Unauthorized to create a resource for this package'))

    package_type = pkg_dict['type'] or 'dataset'

    errors = errors or {}
    error_summary = error_summary or {}
    extra_vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                  'resource_form_snippet': resource_form(package_type), 'dataset_type': package_type,
                  'pkg_name': id}
    # get resources for sidebar
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
    try:
        pkg_dict = get_action('package_show')(context, {'id': id})
    except NotFound:
        abort(404, _('The dataset {id} could not be found.').format(id=id))
    # required for nav menu
    extra_vars['pkg_dict'] = pkg_dict
    template = 'package/new_resource_not_draft.html'
    if pkg_dict['state'] == 'draft':
        extra_vars['stage'] = ['complete', 'active']
        template = 'package/new_resource.html'
    elif pkg_dict['state'] == 'draft-complete':
        extra_vars['stage'] = ['complete', 'active', 'complete']
        template = 'package/new_resource.html'
    return render(template, extra_vars=extra_vars)


# AJAX validator
# class DatasetValidator(BaseController):
#     """Controller to validate resource"""


def dv_check_if_unique(unique_id, owner_org, pkg_name):
    packages = dv_get_packages(owner_org)
    for package in packages:
        for extra in package['extras']:
            if extra['key'] == 'unique_id' and extra['value'] == unique_id and pkg_name != package['id']:
                return package['name']
    return False


def dv_get_packages(owner_org):
    # Build the data.json file.
    packages = dv_get_all_group_packages(group_id=owner_org)
    # get packages for sub-agencies.
    sub_agency = model.Group.get(owner_org)
    if 'sub-agencies' in list(sub_agency.extras.col.keys()) \
            and sub_agency.extras.col['sub-agencies'].state == 'active':
        sub_agencies = sub_agency.extras.col['sub-agencies'].value
        sub_agencies_list = sub_agencies.split(",")
        for sub in sub_agencies_list:
            sub_packages = dv_get_all_group_packages(group_id=sub)
            for sub_package in sub_packages:
                packages.append(sub_package)

    return packages


def dv_get_all_group_packages(group_id):
    """
    Gets all of the group packages, public or private, returning them as a list of CKAN's dictized packages.
    """
    result = []
    for pkg_rev in model.Group.get(group_id).packages(with_private=True, context={'user_is_admin': True}):
        result.append(model_dictize.package_dictize(pkg_rev, {'model': model}))

    return result


def dv_validate_dataset():
    try:
        pkg_name = request.params.get('pkg_name', False)
        owner_org = request.params.get('owner_org', False)
        unique_id = request.params.get('unique_id', False)
        rights = request.params.get('rights', False)
        license_url = request.params.get('license_url', False)
        temporal = request.params.get('temporal', False)
        described_by = request.params.get('described_by', False)
        described_by_type = request.params.get('described_by_type', False)
        conforms_to = request.params.get('conforms_to', False)
        landing_page = request.params.get('landing_page', False)
        language = request.params.get('language', False)
        investment_uii = request.params.get('investment_uii', False)
        references = request.params.get('references', False)
        issued = request.params.get('issued', False)
        system_of_records = request.params.get('system_of_records', False)

        errors = {}
        warnings = {}

        matching_package = dv_check_if_unique(unique_id, owner_org, pkg_name)
        if unique_id and matching_package:
            errors['unique_id'] = 'Already being used by ' + request.host_url + '/dataset/' \
                                  + matching_package
        if rights and len(rights) > 255:
            errors['access-level-comment'] = 'The length of the string exceeds limit of 255 chars'

        dv_check_url(license_url, errors, warnings, 'license-new', True, True)
        dv_check_url(described_by, errors, warnings, 'data_dictionary', True, True)
        dv_check_url(conforms_to, errors, warnings, 'conforms_to', True, True)
        dv_check_url(landing_page, errors, warnings, 'homepage_url', True, True)
        dv_check_url(system_of_records, errors, warnings, 'system_of_records')

        if described_by_type and not IANA_MIME_REGEX.match(described_by_type) \
                and not REDACTED_REGEX.match(described_by_type):
            errors['data_dictionary_type'] = 'The value is not valid IANA MIME Media type'

        if temporal and not REDACTED_REGEX.match(temporal):
            if "/" not in temporal:
                errors['temporal'] = 'Invalid Temporal Format. Missing slash'
            elif not TEMPORAL_REGEX_1.match(temporal) \
                    and not TEMPORAL_REGEX_2.match(temporal) \
                    and not TEMPORAL_REGEX_3.match(temporal):
                errors['temporal'] = 'Invalid Temporal Format'

        if language:  # and not REDACTED_REGEX.match(language):
            language = language.split(',')
            for s in language:
                s = s.strip()
                if not LANGUAGE_REGEX.match(s):
                    errors['language'] = 'Invalid Language Format: ' + str(s)

        if investment_uii and not REDACTED_REGEX.match(investment_uii):
            if not PRIMARY_IT_INVESTMENT_UII_REGEX.match(investment_uii):
                errors['primary-it-investment-uii'] = 'Invalid Format. Must be `023-000000001` format'

        if references and not REDACTED_REGEX.match(references):
            references = references.split(',')
            for s in references:
                url = s.strip()
                if not URL_REGEX.match(url) and not REDACTED_REGEX.match(url):
                    errors['related_documents'] = 'One of urls is invalid: ' + url

        if issued and not REDACTED_REGEX.match(issued):
            if not ISSUED_REGEX.match(issued):
                errors['release_date'] = 'Invalid Format'

        if errors:
            return json.dumps({'ResultSet': {'Invalid': errors, 'Warnings': warnings}})
        return json.dumps({'ResultSet': {'Success': errors, 'Warnings': warnings}})
    except Exception as ex:
        log.error('validate_resource exception: %s ', ex)
        return json.dumps({'ResultSet': {'Error': 'Unknown error'}})


def dv_check_url(url, errors, warnings, error_key, skip_empty=True, allow_redacted=False):
    if skip_empty and not url:
        return
    url = url.strip()
    if allow_redacted and REDACTED_REGEX.match(url):
        return
    if not URL_REGEX.match(url):
        errors[error_key] = 'Invalid URL format'
    return
    # else:
    # try:
    # r = requests.head(url, verify=False)
    # if r.status_code > 399:
    # r = requests.get(url, verify=False)
    # if r.status_code > 399:
    # warnings[error_key] = 'URL returns status ' + str(r.status_code) + ' (' + str(r.reason) + ')'
    # except Exception as ex:
    # log.error('check_url exception: %s ', ex)
    #         warnings[error_key] = 'Could not check url'


# AJAX validator
# class ResourceValidator(BaseController):
#     """Controller to validate resource"""


def rv_validate_resource():
    try:
        url = request.params.get('url', False)
        resource_type = request.params.get('resource_type', False)
        described_by = request.params.get('describedBy', False)
        described_by_type = request.params.get('describedByType', False)
        conforms_to = request.params.get('conformsTo', False)
        media_type = request.params.get('format', False)

        errors = {}
        warnings = {}

        # if media_type and not REDACTED_REGEX.match(media_type) \
        #         and not IANA_MIME_REGEX.match(media_type):
        # if media_type and not IANA_MIME_REGEX.match(media_type):
        #     errors['format'] = 'The value is not valid IANA MIME Media type'
        # elif not media_type and resource_type in ['file', 'upload']:
        #     if url or resource_type == 'upload':
        #         errors['format'] = 'The value is required for this type of resource'

        lower_types = [mtype.lower() for mtype in local_helper.media_types]
        if media_type and media_type.lower() not in lower_types:
            errors['format'] = 'The value is not valid format'
        elif not media_type and resource_type in ['file', 'upload']:
            if url or resource_type == 'upload':
                errors['format'] = 'The value is required for this type of resource'

        rv_check_url(described_by, errors, warnings, 'describedBy', True, True)
        rv_check_url(conforms_to, errors, warnings, 'conformsTo', True, True)

        if described_by_type and not REDACTED_REGEX.match(described_by_type.strip()) \
                and not IANA_MIME_REGEX.match(described_by_type.strip()):
            errors['describedByType'] = 'The value is not valid IANA MIME Media type'

        if errors:
            return json.dumps({'ResultSet': {'Invalid': errors, 'Warnings': warnings}})
        return json.dumps({'ResultSet': {'Success': errors, 'Warnings': warnings}})
    except Exception as ex:
        log.error('validate_resource exception: %s ', ex)
        return json.dumps({'ResultSet': {'Error': 'Unknown error'}})


def rv_check_url(url, errors, warnings, error_key, skip_empty=True, allow_redacted=False):
    if skip_empty and not url:
        return
    url = url.strip()
    if allow_redacted and REDACTED_REGEX.match(url):
        return
    if not URL_REGEX.match(url):
        errors[error_key] = 'Invalid URL format'
    else:
        try:
            r = requests.head(url, verify=False)
            if r.status_code > 399:
                r = requests.get(url, verify=False)
                if r.status_code > 399:
                    warnings[error_key] = 'URL returns status ' + str(r.status_code) + ' (' + str(r.reason) + ')'
        except Exception as ex:
            log.error('check_url exception: %s ', ex)
            warnings[error_key] = 'Could not check url'


# class CloneController(BaseController):
#     """Controller to clone dataset metadata"""


def cc_clone_dataset_metadata(id):
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
    pkg_dict = get_action('package_show')(context, {'id': id})

    # udpate name and title
    pkg_dict['title'] = "Clone of " + pkg_dict['title']

    # name can not be more than 100 characters
    pkg_dict['name'] = pkg_dict['name'][:85] + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    pkg_dict['state'] = 'draft'
    pkg_dict['tag_string'] = ['']
    # remove id from original dataset
    if 'id' in pkg_dict:
        del pkg_dict['id']

    # remove resource for now.
    if 'resources' in pkg_dict:
        del pkg_dict['resources']

    # extras have to on top level. otherwise validation fails
    temp = {}
    for extra in pkg_dict['extras']:
        temp[extra['key']] = extra['value']

    del pkg_dict['extras']
    pkg_dict['extras'] = []
    for key, value in temp.items():
        if key != 'title':
            pkg_dict[key] = value

    # somehow package is getting added to context. If we dont remove it current dataset gets updated
    if 'package' in context:
        del context['package']

    # disabling validation
    context['cloning'] = True

    # create new package
    pkg_dict_new = get_action('package_create')(context, pkg_dict)

    # redirect to draft edit
    redirect(h.url_for(controller='package', action='edit', id=pkg_dict_new['name']))


# class CurlController(BaseController):
#     """Controller to obtain info by url"""


def cuc_get_content_type():
    # set content type (charset required or pylons throws an error)
    try:
        url = request.params.get('url', '')

        if REDACTED_REGEX.match(url):
            return json.dumps({'ResultSet': {
                'CType': False,
                'Status': 'OK',
                'Redacted': True,
                'Reason': '[[REDACTED]]'
            }})

        if not URL_REGEX.match(url):
            return json.dumps({'ResultSet': {'Error': 'Invalid URL', 'InvalidFormat': 'True', 'Red': 'True'}})

        r = requests.head(url, verify=False)
        method = 'HEAD'
        if r.status_code > 399 or r.headers.get('content-type') is None:
            r = requests.get(url, verify=False)
            method = 'GET'
            if r.status_code > 399 or r.headers.get('content-type') is None:
                # return json.dumps({'ResultSet': {'Error': 'Returned status: ' + str(r.status_code)}})
                return json.dumps({'ResultSet': {
                    'CType': False,
                    'Status': r.status_code,
                    'Reason': r.reason,
                    'Method': method}})
        content_type = r.headers.get('content-type')
        content_type = content_type.split(';', 1)
        unified_format = h.unified_resource_format(content_type[0])
        return json.dumps({'ResultSet': {
            'CType': unified_format,
            'Status': r.status_code,
            'Reason': r.reason,
            'Method': method}})
    except Exception as ex:
        log.error('get_content_type exception: %s ', ex)
        return json.dumps({'ResultSet': {'Error': 'unknown error'}})
        # return json.dumps({'ResultSet': {'Error': type(e).__name__}})


# class MediaController(BaseController):
#     """Controller to return the acceptable media types as JSON, powering the front end"""


def mc_get_media_types():
    # set content type (charset required or pylons throws an error)
    q = request.params.get('incomplete', '').lower()

    response.content_type = 'application/json; charset=UTF-8'

    retval = []

    if q in local_helper.media_types_dict:
        retval.append(local_helper.media_types_dict[q][1])

    media_keys = list(local_helper.media_types_dict.keys())
    for media_type in media_keys:
        if q in media_type.lower() and local_helper.media_types_dict[media_type][1] not in retval:
            retval.append(local_helper.media_types_dict[media_type][1])
        if len(retval) >= 50:
            break

    return json.dumps({'ResultSet': {'Result': retval}})

# class LicenseURLController(BaseController):
#     """Controller to return the acceptable media types as JSON, powering the front end"""


def lc_get_license_url():
    # set content type (charset required or pylons throws an error)

    response.content_type = 'application/json; charset=UTF-8'

    retval = []

    for key in local_helper.license_options:
        retval.append(key)

    return json.dumps({'ResultSet': {'Result': retval}})


datapusher.add_url_rule('/dataset/new_resource/<id>',
                        view_func=new_resource_usmetadata)
datapusher.add_url_rule('/api/2/util/resource/license_url_autocomplete',
                        view_func=lc_get_license_url)
datapusher.add_url_rule('/dataset/<id>/clone',
                        view_func=cc_clone_dataset_metadata)

datapusher.add_url_rule('/api/2/util/resource/media_autocomplete',
                        view_func=mc_get_media_types)
datapusher.add_url_rule('/api/2/util/resource/content_type',
                        view_func=cuc_get_content_type)
datapusher.add_url_rule('/api/2/util/resource/validate_resource',
                        view_func=rv_validate_resource)
datapusher.add_url_rule('/api/2/util/resource/validate_dataset',
                        view_func=dv_validate_dataset)
