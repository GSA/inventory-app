describe('Dataset', () => {

    before(() => {
        cy.create_token();
        cy.logout();
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');
    });
    
    after(() => {
        cy.delete_dataset('test-dataset-1');
        cy.delete_organization('test-organization');
        cy.revoke_token();
    });

    it('Creates dataset via API', () => {
        cy.fixture('ckan_dataset.json').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
    });

    it('Has a details page with core metadata', () => {
        cy.login();
        cy.visit('/dataset/test-dataset-1');
        cy.contains('Test Dataset 1');
        cy.contains('DCAT-US Metadata');
    });

    it('Add resource to private dataset via API', () => {
        const token_data = Cypress.env('token_data');
        cy.logout();
        cy.fixture('ckan_resource.csv', 'binary').then((ckan_resource) => {
            // File in binary format gets converted to blob so it can be sent as Form data
            const blob = Cypress.Blob.binaryStringToBlob(ckan_resource)
            const formData = new FormData();
            formData.append('upload', blob, 'ckan_resource.csv'); //adding a file to the form
            formData.append('package_id', "test-dataset-1");
            formData.append('name', "test-resource-1");
            formData.append('resource_type', "CSV");
            formData.append('format', "CSV");
            cy.request({
                method: 'POST',
                url: '/api/action/resource_create',
                body: formData,
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'X-CKAN-API-Key': token_data.api_token
                }
            }).then((response) => {
                expect(response.status).to.eq(200);
            });
        });
    });

    it('Download resource file', () => {
        cy.login();
        cy.visit('/dataset/test-dataset-1')
        // Open resource dropdown
        cy.get('.dropdown-toggle').click()
        // Download resource file
        cy.get('a[href*="ckan_resource.csv"]').click({force: true})
        // check downloaded file matches uploaded file header
        cy.task('isExistFile', 'ckan_resource.csv').should('contain', 'for,testing,purposes');
    });

    it('Download resource file', () => {
        // Test download as anonymous user

        cy.login();
        cy.visit('/dataset/test-dataset-1')
        // Open resource dropdown
        cy.get('.dropdown-toggle').click();
        // Download resource file
        cy.get('a[href*="ckan_resource.csv"]').click({force: true}).should('have.attr', 'href').then((href) => {
            cy.logout();
            cy.request(href).then((response) => {
              cy.writeFile('cypress/downloads/ckan_resource2.csv', response.body)
            });
            cy.task('isExistFile', 'ckan_resource2.csv').should('contain', 'for,testing,purposes');
        });
    });
})
