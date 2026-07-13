import 'cypress-file-upload';

describe('DCAT-US v3.0 Export', () => {
    before(() => {
        cy.create_token();
    });

    beforeEach(() => {
        cy.logout();
        cy.delete_dataset('test-dataset-1');
        cy.delete_organization('test-organization');

        cy.create_organization('test-organization', 'Test organization');

        cy.fixture('ckan_dataset').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });

        cy.exec('rm cypress/downloads/dcat-us-v3*', { failOnNonZeroExit: false });
        cy.login();
    });

    after(() => {
        cy.logout();
        cy.delete_dataset('test-dataset-1');
        cy.delete_organization('test-organization');
        cy.exec('rm cypress/downloads/dcat-us-v3*', { failOnNonZeroExit: false });
        cy.revoke_token();
    });

    it('Can create a DCAT-US v3.0 export of organization datasets', () => {
        cy.downloadFile(
            Cypress.config().baseUrl + '/organization/test-organization/dcat-us-v3.json',
            'cypress/downloads',
            'dcat-us-v3.zip'
        );

        cy.exec('unzip cypress/downloads/dcat-us-v3.zip -d cypress/downloads');
        cy.exec('test -f cypress/downloads/dcat-us-v3.json').its('code').should('eq', 0);
    });

    it('DCAT-US v3.0 export contains valid JSON with required fields', () => {
        cy.downloadFile(
            Cypress.config().baseUrl + '/organization/test-organization/dcat-us-v3.json',
            'cypress/downloads',
            'dcat-us-v3.zip'
        );

        cy.exec('unzip -o cypress/downloads/dcat-us-v3.zip -d cypress/downloads');

        cy.readFile('cypress/downloads/dcat-us-v3.json').then((jsonContent) => {
            expect(jsonContent).to.be.an('object');
            expect(jsonContent).to.have.property('@context');
            expect(jsonContent).to.have.property('conformsTo');
            expect(jsonContent.dataset).to.be.an('array');
        });

        cy.exec("grep -q 'Test Dataset 1' cypress/downloads/dcat-us-v3.json").its('code').should('eq', 0);
    });
});
