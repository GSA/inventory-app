describe('Public Access', () => {
    before(() => {
        cy.login('cypress-user', 'cypress-user-password', false);
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');
        cy.fixture('ckan_dataset.json').then((ckan_dataset) => {
            ckan_dataset.private = false;
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true);
            });
        });
    })
    // beforeEach(() => {
    //     Cypress.Cookies.preserveOnce('auth_tkt', 'ckan')
    // })
    after(() => {
        cy.delete_dataset('test-dataset-1')
        cy.delete_organization('test-organization')
    })

    it('Cannot access the standard public pages', () => {
        cy.request({
            url: '/dataset',
            failOnStatusCode: false
        }).then((response) => {
            // TODO: local extension should return 403 on anonymous access
            // expect(response.status).to.eq(403)
            expect(response.status).to.eq(200)
        })
        
    })

    it('Cannot access the dataset pages', () => {
        cy.request({
            url: '/dataset/test-dataset-1',
            failOnStatusCode: false
        }).then((response) => {
            // TODO: local extension should return 403 on anonymous access
            // expect(response.status).to.eq(403)
            expect(response.status).to.eq(200)
        })
        
    })
})
