describe('DCAT-US Export', () => {

    beforeEach(() => {
        cy.logout();
        cy.login();
        cy.delete_dataset('test-dataset-1')
        cy.delete_dataset('test-dataset-2')
        cy.delete_dataset('draft-dataset-1')
        cy.delete_dataset('draft-dataset-2')
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');

        // Create 3 datasets, 2 being drafts
        cy.fixture('ckan_dataset').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true)
            });
        });
        cy.fixture('draft_data_1').then((draft_data_1) => {
            cy.create_dataset(draft_data_1).should((response) => {
                expect(response.body).to.have.property('success', true)
            });
        });
        cy.fixture('draft_data_2').then((draft_data_2) => {
            cy.create_dataset(draft_data_2).should((response) => {
                expect(response.body).to.have.property('success', true)
            });
        });
        cy.exec('rm cypress/downloads/draft*', {failOnNonZeroExit: false});
    })
    
    afterEach(() => {
        cy.delete_dataset('test-dataset-1')
        cy.delete_dataset('test-dataset-2')
        cy.delete_dataset('draft-dataset-1')
        cy.delete_dataset('draft-dataset-2')
        cy.delete_organization('test-organization')
        cy.exec('rm cypress/downloads/draft*', {failOnNonZeroExit: false});
    })

    it('Can create a zip export of the organization', () => {
        cy.downloadFile('http://localhost:5000/organization/test-organization/draft.json',
                            'cypress/downloads', 'draft.zip')

        cy.exec('unzip cypress/downloads/draft.zip -d cypress/downloads');
        cy.exec('grep -q \'Test Dataset 1\' cypress/downloads/draft_data.json', { failOnNonZeroExit: false })
            .its('code').should('eq', 1);
        cy.exec('grep -q \'Draft Dataset 1\' cypress/downloads/draft_data.json')
            .its('code').should('eq', 0);
        cy.exec('grep -q \'Draft Dataset 2\' cypress/downloads/draft_data.json')
            .its('code').should('eq', 0);

    })

    // TODO: integrate dcat_usmetadata form
    it('Submit Required Metadata works', () => {
        cy.visit('/dataset/new-metadata');
        cy.requiredMetadata('test-dataset-2');
        cy.contains('Dataset saved successfully');
    });
})
