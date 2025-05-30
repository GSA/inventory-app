describe('CKAN Token', () => {

    before(() => {
        cy.create_token();
    });

    after(() => {
        cy.revoke_token();
    });
    
    it('Can get CKAN token', () => {
        const token_data = Cypress.env('token_data');
        expect(token_data.api_token).to.have.length(175);
        expect(token_data.jti).to.have.length(43);
    });

    it('Can authorize with token', () => {
        const token_data = Cypress.env('token_data');
        cy.logout();

        // 403 without token
        cy.request({
            method: 'GET',
            url: '/api/action/package_search',
            failOnStatusCode: false,
        }).then((response) => {
            expect(response.status).to.eq(403);
        });

        // 200 with token
        cy.request({
            method: 'GET',
            url: '/api/action/package_search',
            headers: {
                'X-CKAN-API-Key': token_data.api_token
            }
        }).then((response) => {
            expect(response.status).to.eq(200);
        });
    });

})
