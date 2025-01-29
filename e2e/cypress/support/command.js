require('cypress-downloadfile/lib/downloadFileCommand');
import Chance from 'chance';
const chance = new Chance();

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
    cy.logout();
    cy.visit('/user/login');

    if (!userName) {
        userName = Cypress.env('USER');
        cy.log(userName, process.env);
    }
    if (!password) {
        password = Cypress.env('USER_PASSWORD');
    }

    // Hide flask debug toolbar
    cy.get('#flDebugHideToolBarButton').click();

    cy.get('#field-login').type(userName);
    cy.get('#field-password').type(password);
    cy.get('.btn-primary').click();

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
        // find the token in <code> tag and save it for later use
        // find the token id (jti) somewhere in the form
        cy.get('div.alert-success code').invoke('text').then((text1) => {
            cy.get('form[action^="/user/' + userName +'/api-tokens/"]').invoke('attr', 'action').then((text2) => {
                const jti = text2.split('/')[4]
                Cypress.env('token_data', { api_token: text1, jti: jti });
            })
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
        headers: {
            'Authorization': token_data.api_token,
            'Content-Type': 'application/json'
        },
        body: {jti: token_data.jti}
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
    const token_data = Cypress.env('token_data');

    let request_obj = {
        url: '/api/action/organization_create',
        method: 'POST',
        headers: {
            'Authorization': token_data.api_token,
            'Content-Type': 'application/json'
        },
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
    const token_data = Cypress.env('token_data');

    cy.request({
        url: '/api/action/organization_delete',
        method: 'POST',
        failOnStatusCode: false,
        headers: {
            'Authorization': token_data.api_token,
            'Content-Type': 'application/json'
        },
        body: {
            id: orgName? orgName: 'test-organization'
        },
    });

    cy.request({
        url: '/api/action/organization_purge',
        method: 'POST',
        failOnStatusCode: false,
        headers: {
            'Authorization': token_data.api_token,
            'Content-Type': 'application/json'
        },
        body: {
            id: orgName? orgName: 'test-organization'
        },
    });
});


Cypress.Commands.add('delete_dataset', (datasetName) => {
    /**
     * Method to purge a dataset from the current state
     * :PARAM datasetName String: Name of the dataset to purge from the current state
     * :RETURN null:
     */
    const token_data = Cypress.env('token_data');
    cy.request({
        url: '/api/action/dataset_purge',
        method: 'POST',
        failOnStatusCode: false,
        headers: {
            'Authorization': token_data.api_token,
            'Content-Type': 'application/json'
        },
        body: {
            id: datasetName,
        },
    });
});

Cypress.Commands.add(
    'create_harvest_source',
    (dataSourceUrl, harvestTitle, harvestDesc, harvestType, org, harvestTest, invalidTest) => {
        /**
         * Method to create a new CKAN harvest source via the CKAN harvest form
         * :PARAM dataSourceUrl String: URL to source the data that will be harvested
         * :PARAM harvestTitle String: Title of the organization's harvest
         * :PARAM harvestDesc String: Description of the harvest being created
         * :PARAM harvestType String: Harvest source type. Ex: waf, datajson
         * :PARAM org String: Organization that is creating the harvest source
         * :PARAM harvestTest Boolean: Determines if to use UI in harvest source creation test or to follow the UI to create a source
         * :RETURN null:
         */
        if (!harvestTest) {
            cy.visit('/harvest/new');
        }
        if (!invalidTest) {
            cy.get('#field-url').type(dataSourceUrl);
        }
        cy.get('#field-title').type(harvestTitle);
        cy.get('#field-name').then(($field_name) => {
            if ($field_name.is(':visible')) {
                $field_name.type(harvestTitle);
            }
        });

        cy.get('#field-notes').type(harvestDesc);
        cy.get('[type="radio"]').check(harvestType);
        if (harvestType == 'waf') {
            //cy.get('#text').then($text => {
            //    if($text.val() == 'Validation'){
            //
            //    }
            //})
            cy.get('[type="radio"]').check('iso19139ngdc');
        }

        // Set harvest to be public always, per best practices
        cy.get('#field-private_datasets').select('False');

        cy.get('input[name=save]').click();
    }
);

Cypress.Commands.add('delete_harvest_source', (harvestName) => {
    cy.visit('/harvest/admin/' + harvestName);
    cy.contains('Clear').click({ force: true });
    cy.visit('/harvest/delete/' + harvestName + '?clear=True');
});

Cypress.Commands.add('start_harvest_job', (harvestName) => {
    cy.visit('/harvest/' + harvestName);
    cy.contains('Admin').click();
    cy.get('.btn-group>.btn:first-child:not(:last-child):not(.dropdown-toggle)').click({ force: true });
    verify_element_exists();
});

Cypress.Commands.add('create_dataset', (ckan_dataset) => {
    const token_data = Cypress.env('token_data');
    var options = {
        method: 'POST',
        url: '/api/3/action/package_create',
        headers: {
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'Authorization': token_data.api_token,
        },
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
    cy.intercept('/api/3/action/package_create').as('packageCreate');
    const datasetTitle = title || chance.word({ length: 5 });
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
    cy.get('button[type=button]').contains('Save and Continue').click();
    cy.wait('@packageCreate');
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
    cy.get('#resource-option-upload-file').parent('.form-group').click();
    cy.get('label[for=upload]').click();
    cy.get('input#upload').attachFile(yourFixturePath);
    cy.get('input[name=resource\\.conformsTo]').type(chance.url());
});
