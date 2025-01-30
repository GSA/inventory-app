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
        cy.visit('/dataset/new-metadata');
        cy.requiredMetadata(dataset_title);
        cy.contains('Dataset saved successfully');
    });

    it('Save resource file to inventory', () => {
        cy.visit('/dataset/new-metadata');
        cy.requiredMetadata(dataset_title);
        cy.additionalMetadata();
        cy.get('button[type=button]')
            .contains('Save and Continue')
            .click()
            .then(() => {
                cy.resourceUpload();
                cy.get('button[type=button]')
                    .contains('Finish and publish')
                    .click()
                    .then(() => {
                        cy.get('.resource-list').find('.resource-item').should('have.length', 1);
                        // Test that the dataset is non-private when uploading a file
                        cy.request('/api/3/action/package_show?id=' + dataset_title).then((response) => {
                            expect(response.status).to.eq(200);
                            expect(response.body.result.private).to.equal(false);
                            expect(response.body.result.resources[0].conformsTo).to.exist;
                        });
                    });
            });
    });
});
