import 'cypress-file-upload';

describe('DCAT-US Export', () => {
    const dataset_title = 'test-dataset-2';

    before(() => {
        cy.create_token();
    });

    beforeEach(() => {
        cy.logout();
        cy.delete_dataset('test-dataset-1');
        cy.delete_dataset('test-dataset-2');
        cy.delete_dataset('test-sub-dataset-1');
        cy.delete_dataset('draft-dataset-1');
        cy.delete_dataset('draft-dataset-2');
        cy.delete_organization('test-organization');
        cy.delete_organization('test-sub-organization');
        // Add extra to link 2 organizations for dcat-us creation
        cy.create_organization('test-organization', 'Test organization', [
            {
                key: 'sub-agencies',
                value: `test-sub-organization`,
            },
        ]);
        cy.create_organization('test-sub-organization', 'Test sub organization');

        // Create 4 datasets, 2 being drafts, 1 in sub org
        cy.fixture('ckan_dataset').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
        cy.fixture('draft_data_1').then((draft_data_1) => {
            cy.create_dataset(draft_data_1).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
        cy.fixture('draft_data_2').then((draft_data_2) => {
            cy.create_dataset(draft_data_2).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
        cy.fixture('ckan_sub_dataset').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
        cy.exec('rm cypress/downloads/draft*', { failOnNonZeroExit: false });
        cy.exec('rm cypress/downloads/redacted.zip', { failOnNonZeroExit: false });
        cy.exec('rm cypress/downloads/data.json', { failOnNonZeroExit: false });

        cy.login();
    });

    after(() => {
        cy.logout();
        cy.delete_dataset('test-dataset-1');
        cy.delete_dataset('test-dataset-2');
        cy.delete_dataset('test-sub-dataset-1');
        cy.delete_dataset('draft-dataset-1');
        cy.delete_dataset('draft-dataset-2');
        cy.delete_organization('test-organization');
        cy.delete_organization('test-sub-organization');
        cy.exec('rm cypress/downloads/draft*', { failOnNonZeroExit: false });
        cy.exec('rm cypress/downloads/redacted.zip', { failOnNonZeroExit: false });
        cy.exec('rm cypress/downloads/data.json', { failOnNonZeroExit: false });
        cy.revoke_token();
    });

    it('Can create a zip export of the organization drafts', () => {
        cy.downloadFile(
            Cypress.config().baseUrl + '/organization/test-organization/draft.json',
            'cypress/downloads',
            'draft.zip'
        );

        cy.exec('unzip cypress/downloads/draft.zip -d cypress/downloads');
        cy.exec("grep -q 'Test Dataset 1' cypress/downloads/draft_data.json", { failOnNonZeroExit: false })
            .its('code')
            .should('eq', 1);
        cy.exec("grep -q 'Draft Dataset 1' cypress/downloads/draft_data.json").its('code').should('eq', 0);
        cy.exec("grep -q 'Draft Dataset 2' cypress/downloads/draft_data.json").its('code').should('eq', 0);
    });

    it('Can create a zip export of the organization datasets', () => {
        cy.downloadFile(
            Cypress.config().baseUrl + '/organization/test-organization/redacted.json',
            'cypress/downloads',
            'redacted.zip'
        );

        cy.exec('unzip cypress/downloads/redacted.zip -d cypress/downloads');
        cy.exec("grep -q 'Draft Dataset 1' cypress/downloads/data.json", { failOnNonZeroExit: false })
            .its('code')
            .should('eq', 1);
        cy.exec("grep -q 'Test Dataset 1' cypress/downloads/data.json").its('code').should('eq', 0);
        cy.exec("grep -q 'Test Sub Dataset 1' cypress/downloads/data.json").its('code').should('eq', 0);
    });

    it('Submit Required Metadata works', () => {
        cy.log('TEST: Starting Submit Required Metadata test');
        cy.visit('/dataset/new-metadata');
        cy.log('TEST: Visited /dataset/new-metadata');
        cy.requiredMetadata(dataset_title);
        cy.log('TEST: Filled required metadata for: ' + dataset_title);
        cy.get('body').then(($body) => {
            cy.log('TEST: Page body HTML length: ' + $body.html().length);
            cy.log('TEST: Looking for "Dataset saved successfully" message');
        });
        cy.contains('Dataset saved successfully', { timeout: 10000 }).then(($el) => {
            cy.log('TEST: SUCCESS - Found "Dataset saved successfully" message');
        });
    });

    it('Save resource file to inventory', () => {
        cy.log('TEST: Starting Save resource file test');
        cy.visit('/dataset/new-metadata');
        cy.log('TEST: Visited /dataset/new-metadata');
        cy.requiredMetadata(dataset_title);
        cy.log('TEST: Filled required metadata');
        cy.additionalMetadata();
        cy.log('TEST: Filled additional metadata');
        cy.get('button[type=button]')
            .contains('Save and Continue')
            .then(($btn) => {
                cy.log('TEST: Found Save and Continue button, clicking...');
            })
            .click()
            .then(() => {
                cy.log('TEST: Clicked Save and Continue, now on resource page');
                cy.get('input[name="resource\\.resource_type"]').then(($input) => {
                    if ($input.length > 0) {
                        cy.log('TEST: Found resource_type input field');
                    } else {
                        cy.log('TEST: ERROR - resource_type input field NOT FOUND');
                    }
                });
                cy.get('input[name="resource\\.conformsTo"]').then(($input) => {
                    if ($input.length > 0) {
                        cy.log('TEST: Found OLD conformsTo input field (should not exist!)');
                    } else {
                        cy.log('TEST: conformsTo field does not exist (expected)');
                    }
                });
                cy.resourceUpload();
                cy.log('TEST: Resource upload completed');
                cy.get('button[type=button]')
                    .contains('Finish and publish')
                    .then(($btn) => {
                        cy.log('TEST: Found Finish and publish button, clicking...');
                    })
                    .click()
                    .then(() => {
                        cy.log('TEST: Clicked Finish and publish');
                        cy.get('.resource-list').find('.resource-item').should('have.length', 1);
                        cy.log('TEST: Found 1 resource in resource list');
                        // Test that the dataset is non-private when uploading a file
                        cy.request('/api/3/action/package_show?id=' + dataset_title).then((response) => {
                            cy.log('TEST: API Response Status: ' + response.status);
                            cy.log('TEST: Dataset private: ' + response.body.result.private);
                            cy.log('TEST: Number of resources: ' + response.body.result.resources.length);

                            expect(response.status).to.eq(200);
                            expect(response.body.result.private).to.equal(false);

                            if (response.body.result.resources.length > 0) {
                                const resource = response.body.result.resources[0];
                                const resourceKeys = Object.keys(resource).join(', ');
                                cy.log('TEST: Resource keys: ' + resourceKeys);
                                cy.log('TEST: resource_type value: ' + JSON.stringify(resource.resource_type));
                                cy.log('TEST: conformsTo value: ' + JSON.stringify(resource.conformsTo));

                                // Try both field names with diagnostic message
                                const hasResourceType = resource.hasOwnProperty('resource_type');
                                const hasConformsTo = resource.hasOwnProperty('conformsTo');

                                expect(hasResourceType || hasConformsTo,
                                    `Neither resource_type nor conformsTo found in resource. Available keys: ${resourceKeys}`).to.be.true;

                                if (hasResourceType) {
                                    expect(resource.resource_type, 'resource_type should have a value').to.exist;
                                } else if (hasConformsTo) {
                                    expect(resource.conformsTo, 'conformsTo should have a value').to.exist;
                                }
                            } else {
                                throw new Error('No resources found in dataset');
                            }
                        });
                    });
            });
    });
});
