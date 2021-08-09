describe('DCAT-US Export', () => {
    before(() => {
        cy.login('cypress-user', 'cypress-user-password', false);
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
    })
    beforeEach(() => {
        Cypress.Cookies.preserveOnce('auth_tkt', 'ckan')
    })
    after(() => {
        cy.delete_dataset('test-dataset-1')
        cy.delete_dataset('draft-dataset-1')
        cy.delete_dataset('draft-dataset-2')
        cy.delete_organization('test-organization')
    })

    // TODO: integrate datajson and usmetadata extensions
    // it('Can create a zip export of the organization', () => {
    //     cy.request('/organization/test-organization/draft.json')
    //     .then((response) => {
    //         cy.log(response.status, response.body);
    //     })
    // })

    // unzip response
    // Validate that there are 2 files, draft_data.json and data.json
    // Read files and validate content (dataset titles)
})
