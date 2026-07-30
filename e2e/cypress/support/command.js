require('cypress-downloadfile/lib/downloadFileCommand');
import Chance from 'chance';
const chance = new Chance();

function get_token_jti(api_token) {
    const token_payload = api_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const decoded_payload = JSON.parse(atob(token_payload));
    return decoded_payload.jti;
}

function api_headers(extra_headers = {}) {
    const token_data = Cypress.env('token_data');
    const csrf_token = Cypress.$('meta[name="_csrf_token"]').attr('content');
    const headers = {
        'X-CKAN-API-Key': token_data.api_token,
        'Content-Type': 'application/json',
        ...extra_headers,
    };

    if (csrf_token) {
        headers['X-CSRFToken'] = csrf_token;
    }

    return headers;
}

function verify_element_exists() {
    cy.get('td')
        .eq(4)
        .then(($td) => {
            if ($td.text() == 'Finished') {
                cy.wrap($td.text()).should('eq', 'Finished');
            } else {
                cy.wait(10000);
                cy.reload(true);
                verify_element_exists();
            }
        });
}

Cypress.Commands.add('login', (userName, password) => {
    /**
     * Method to fill and submit the CKAN Login form
     * :PARAM userName String: user name of that will be attempting to login
     * :PARAM password String: password for the user logging in
     * :RETURN null:
     */
    cy.log('LOGIN: Starting login process');
    cy.logout();
    cy.log('LOGIN: Visiting /user/login');
    cy.visit('/user/login');

    if (!userName) {
        userName = Cypress.env('USER');
        cy.log('LOGIN: Using default user from env: ' + userName);
    } else {
        cy.log('LOGIN: Logging in as: ' + userName);
    }
    if (!password) {
        password = Cypress.env('USER_PASSWORD');
    }

    // Hide flask debug toolbar
    cy.log('LOGIN: Hiding debug toolbar');
    cy.get('#flDebugHideToolBarButton', { timeout: 5000 }).click();

    cy.log('LOGIN: Filling login form');
    cy.get('#field-login', { timeout: 5000 }).type(userName);
    cy.get('#field-password', { timeout: 5000 }).type(password);
    cy.log('LOGIN: Submitting login form');
    cy.get('.btn-primary').click();
    cy.log('LOGIN: Login form submitted');

});

Cypress.Commands.add('logout', () => {
    cy.clearCookies();
});


Cypress.Commands.add('create_token', (tokenName) => {
    // return if token already exists
    const token_data = Cypress.env('token_data');
    
    if (token_data) {
        cy.log('Token already exists. skipping token creation.');
        return;
    }
    
    cy.login();

    if (!tokenName) {
        tokenName = 'cypress token';
    }

    const userName = Cypress.env('USER');
    // create an API token named 'cypress token'
    cy.visit('/user/' + userName + '/api-tokens');

    cy.get('body').then($body => {
        cy.get('#name').type('cypress token');
        cy.get('button[value="create"]').click();
        // Find the token in the success alert and save its JWT id for revocation.
        cy.get('div.alert-success code').invoke('text').then((api_token) => {
            api_token = api_token.trim();
            const jti = get_token_jti(api_token);
            Cypress.env('token_data', { api_token: api_token, jti: jti });
        });
        cy.log('cypress token created.');
    });

});

Cypress.Commands.add('revoke_token', (tokenName) => {

    const token_data = Cypress.env('token_data');

    if (!token_data) {
        return;
    }

    if (!tokenName) {
        tokenName = 'cypress token';
    }
    cy.log('Revoking cypress token.......');
    cy.request({
        url: '/api/3/action/api_token_revoke',
        method: 'POST',
        headers: api_headers(),
        body: {jti: token_data.jti}
    }).then(() => {
        Cypress.env('token_data', null);
    });
});


Cypress.Commands.add('create_organization_ui', (orgName, orgDesc) => {
    /**
     * Method to fill out the form to create a CKAN organization
     * :PARAM orgName String: Name of the organization being created
     * :PARAM orgDesc String: Description of the organization being created
     * :PARAM orgTest Boolean: Control value to determine if to use UI to create organization
     *      for testing or to visit the organization creation page
     * :RETURN null:
     */
    cy.get('#field-name').type(orgName);
    cy.get('#field-description').type(orgDesc);
    cy.get('#field-url').then(($field_url) => {
        if ($field_url.is(':visible')) {
            $field_url.type(orgName);
        }
    });
    cy.get('button[name=save]').click();
});

Cypress.Commands.add('create_organization', (orgName, orgDesc, extras = null) => {
    /**
     * Method to create organization via CKAN API
     * :PARAM orgName String: Name of the organization being created
     * :PARAM orgDesc String: Description of the organization being created
     * :PARAM orgTest Boolean: Control value to determine if to use UI to create organization
     *      for testing or to visit the organization creation page
     * :RETURN null:
     */
    let request_obj = {
        url: '/api/action/organization_create',
        method: 'POST',
        headers: api_headers(),
        body: {
            description: orgDesc,
            title: orgName,
            approval_status: 'approved',
            state: 'active',
            name: orgName,
            extras: [
                {
                    key: 'publisher',
                    value: `[["${orgName}", "${orgName}", "top level publisher"], ["${orgName}", "${orgName}", "top level publisher", "first level publisher", "second level publisher"]]`,
                },
            ],
        },
    };

    if (extras) {
        request_obj.body.extras = request_obj.body.extras.concat(extras);
    }

    cy.request(request_obj);
});


Cypress.Commands.add('delete_organization', (orgName) => {
    /**
     * Method to purge an organization from the current state
     * :PARAM orgName String: Name of the organization to purge from the current state
     * :RETURN null:
     */
    cy.request({
        url: '/api/action/organization_delete',
        method: 'POST',
        failOnStatusCode: false,
        headers: api_headers(),
        body: {
            id: orgName? orgName: 'test-organization'
        },
    });

    cy.request({
        url: '/api/action/organization_purge',
        method: 'POST',
        failOnStatusCode: false,
        headers: api_headers(),
        body: {
            id: orgName? orgName: 'test-organization'
        },
    });
});


Cypress.Commands.add('create_user', (userName, userEmail, userPassword) => {
    /**
     * Method to create an user via CKAN API
     * :RETURN null:
     */
    cy.log('CREATE_USER: Creating user: ' + userName + ' with email: ' + userEmail);
    let request_obj = {
        url: '/api/action/user_create',
        method: 'POST',
        failOnStatusCode: false,
        headers: api_headers(),
        body: {
            name: userName,
            email: userEmail,
            password: userPassword
        },
    };

    cy.request(request_obj).then((response) => {
        cy.log('CREATE_USER: Response status: ' + response.status);
        cy.log('CREATE_USER: Response success: ' + response.body.success);
        if (response.status === 409 && response.body.error.name.includes("That login name is not available.")) {
            cy.log("CREATE_USER: User already exists. Make sure it is active");
            request_obj.url = '/api/action/user_patch';
            request_obj.failOnStatusCode = true;
            request_obj.body = {
                id: userName,
                password: userPassword,
                email: userEmail,
                state: "active"
            }
            cy.log('CREATE_USER: Patching existing user');
            cy.request(request_obj).then((patchResponse) => {
                cy.log('CREATE_USER: Patch response status: ' + patchResponse.status);
                cy.log('CREATE_USER: Patch response success: ' + patchResponse.body.success);
            });
        } else if (!response.body.success) {
            cy.log('CREATE_USER: ERROR - User creation failed: ' + JSON.stringify(response.body.error));
        } else {
            cy.log('CREATE_USER: User created successfully');
        }
    });

});


Cypress.Commands.add('assign_user', (orgName, userName, userRole) => {
    /**
     * Method to assign an organization role to an user via CKAN API
     * :RETURN null:
     */
    cy.log('ASSIGN_USER: Assigning user ' + userName + ' to org ' + orgName + ' with role ' + userRole);
    let request_obj = {
        url: '/api/action/organization_member_create',
        method: 'POST',
        failOnStatusCode: true,
        headers: api_headers(),
        body: {
            id: orgName,
            username: userName,
            role: userRole
        },
    };

    cy.request(request_obj).then((response) => {
        cy.log('ASSIGN_USER: Response status: ' + response.status);
        cy.log('ASSIGN_USER: Response success: ' + response.body.success);
        if (!response.body.success) {
            cy.log('ASSIGN_USER: ERROR - Assignment failed: ' + JSON.stringify(response.body.error));
        } else {
            cy.log('ASSIGN_USER: User assigned successfully');
        }
    });

});


Cypress.Commands.add('delete_user', (userName) => {
    /**
     * Method to delete an user via CKAN API
     * :RETURN null:
     */
    cy.log('DELETE_USER: Deleting user: ' + userName);
    let request_obj = {
        method: 'POST',
        failOnStatusCode: false,
        headers: api_headers(),
        body: {
            id: userName
        },
    };

    request_obj.url = '/api/action/user_delete'
    cy.request(request_obj).then((response) => {
        cy.log('DELETE_USER: Response status: ' + response.status);
        cy.log('DELETE_USER: Response success: ' + response.body.success);
        if (!response.body.success) {
            cy.log('DELETE_USER: ERROR - User deletion failed: ' + JSON.stringify(response.body.error));
        } else {
            cy.log('DELETE_USER: User deleted successfully');
        }
    });

});


Cypress.Commands.add('delete_dataset', (datasetName) => {
    /**
     * Method to purge a dataset from the current state
     * :PARAM datasetName String: Name of the dataset to purge from the current state
     * :RETURN null:
     */
    cy.request({
        url: '/api/action/dataset_purge',
        method: 'POST',
        failOnStatusCode: false,
        headers: api_headers(),
        body: {
            id: datasetName,
        },
    });
});

Cypress.Commands.add('create_dataset', (ckan_dataset) => {
    var options = {
        method: 'POST',
        url: '/api/3/action/package_create',
        headers: api_headers({
            'cache-control': 'no-cache',
            'content-type': 'application/json',
        }),
        body: JSON.stringify(ckan_dataset),
    };

    return cy.request(options);
});

// Performs an XMLHttpRequest instead of a cy.request (able to send data as FormData - multipart/form-data)
Cypress.Commands.add('form_request', (method, url, formData, done) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    xhr.onload = function () {
        done(xhr);
    };
    xhr.onerror = function () {
        done(xhr);
    };
    xhr.send(formData);
});

Cypress.Commands.add('requiredMetadata', (title) => {
    cy.log('REQUIRED_METADATA: Starting required metadata fill');
    cy.intercept('/api/3/action/package_create').as('packageCreate');
    const datasetTitle = title || chance.word({ length: 5 });
    cy.log('REQUIRED_METADATA: Dataset title: ' + datasetTitle);
    cy.get('input[name=title]').type(datasetTitle);
    cy.get('textarea[name=description]').type(chance.sentence({ words: 4 }));
    cy.get('.react-tags input').type('1234{enter}');
    cy.get('select[name=owner_org]').select('test-organization');
    cy.get('input[placeholder="Select publisher"]').type('top level publisher');
    cy.get('input[placeholder="Select publisher"]').type('{downarrow}{enter}');
    cy.get('input[name=contact_name]').type(chance.name());
    cy.get('input[name=contact_email]').type(chance.email());
    cy.get('input[name=unique_id]').type(chance.string({ length: 10 }));
    cy.get('select[name=public_access_level]').select('public');
    cy.get('select[name=license]').select('Other');
    cy.get('input[name=licenseOther]').type(chance.url());
    cy.get('#rights_option_1').parent('.form-group').click();
    cy.get('#spatial_option_2').parent('.form-group').click();
    cy.get('input[name=spatial_location_desc]').type(chance.sentence({ words: 2 }));
    cy.get('#temporal_option_2').parent('.form-group').click();
    cy.get('input[name=temporal_start_date]').type('2010-11-11');
    cy.get('input[name=temporal_end_date]').type('2020-11-11');
    cy.log('REQUIRED_METADATA: All fields filled, clicking Save and Continue');
    cy.get('button[type=button]').contains('Save and Continue').click();
    cy.log('REQUIRED_METADATA: Waiting for package_create API call');
    cy.wait('@packageCreate').then((interception) => {
        cy.log('REQUIRED_METADATA: package_create API status: ' + interception.response.statusCode);
        cy.log('REQUIRED_METADATA: package_create success: ' + interception.response.body.success);
        if (!interception.response.body.success) {
            cy.log('REQUIRED_METADATA: ERROR - package_create failed: ' + JSON.stringify(interception.response.body.error));
        }
    });
    cy.log('REQUIRED_METADATA: Required metadata completed');
});

Cypress.Commands.add('additionalMetadata', (isparent) => {
    cy.get('select[name=dataQuality]').select('Yes');
    cy.get('#category-option-yes').parent('.form-group').click();
    cy.get('input[name=data_dictionary]').clear().type(chance.url());
    cy.get('select[name=describedByType]').select('text/csv');
    cy.get('select[name=accrualPeriodicity]').select('R/P1W');
    cy.get('input[name=homepage_url]').clear().type(chance.url());
    cy.get('select[name=languageSubTag]').select('en');
    cy.get('select[name=languageRegSubTag]').select('US');
    cy.get('input[name=primary_it_investment_uii]').type('123-123456789');
    cy.get('input[name=related_documents]').type(chance.name());
    cy.get('input[name=release_date]').type('2020-08-08');
    cy.get('input[name=system_of_records]').type(chance.url());
    if (isparent) {
        cy.get('select[name=isParent]').select('Yes');
    } else {
        cy.get('select[name=isParent]').select('No');
    }
});

Cypress.Commands.add('resourceUpload', () => {
    const yourFixturePath = '../fixtures/ckan_resource.csv';
    cy.log('RESOURCE_UPLOAD: Starting resource upload');
    cy.get('#resource-option-upload-file').parent('.form-group').then(($el) => {
        cy.log('RESOURCE_UPLOAD: Found upload file option, clicking...');
    }).click();
    cy.get('label[for=upload]').then(($el) => {
        cy.log('RESOURCE_UPLOAD: Found upload label, clicking...');
    }).click();
    cy.get('input#upload').attachFile(yourFixturePath);
    cy.log('RESOURCE_UPLOAD: File attached: ' + yourFixturePath);

    // Check which input field exists and fail with diagnostic info if neither found
    cy.get('body').then(($body) => {
        const hasResourceType = $body.find('input[name="resource\\.resource_type"]').length > 0;
        const hasConformsTo = $body.find('input[name="resource\\.conformsTo"]').length > 0;
        const allInputs = $body.find('input').map((i, el) => el.name).get().join(', ');

        cy.log('RESOURCE_UPLOAD: resource_type field exists: ' + hasResourceType);
        cy.log('RESOURCE_UPLOAD: conformsTo field exists: ' + hasConformsTo);
        cy.log('RESOURCE_UPLOAD: All input names on page: ' + allInputs);

        // Assert at least one exists with diagnostic message
        expect(hasResourceType || hasConformsTo,
            `Neither resource_type nor conformsTo field found. Available inputs: ${allInputs}`).to.be.true;
    });

    // Try resource_type first, fallback to conformsTo
    cy.get('body').then(($body) => {
        const hasResourceType = $body.find('input[name="resource\\.resource_type"]').length > 0;
        const fieldName = hasResourceType ? 'resource\\.resource_type' : 'resource\\.conformsTo';
        const url = chance.url();

        cy.log('RESOURCE_UPLOAD: Using field: ' + fieldName);
        cy.log('RESOURCE_UPLOAD: Typing URL: ' + url);
        cy.get(`input[name="${fieldName}"]`, { timeout: 5000 }).should('exist').type(url);
    });
    cy.log('RESOURCE_UPLOAD: Resource upload completed');
});
