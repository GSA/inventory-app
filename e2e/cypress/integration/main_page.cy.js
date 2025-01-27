describe('Main Page', () => {
    
    beforeEach(() => {
        cy.logout();
        cy.login();
    });

    it('Load main page with configuration', () => {
        cy.visit('/dataset');
        cy.contains('Inventory');
    });

    it('google tracker injected', () => {
        cy.request('/dataset').then((response) => {
            expect(response.body).to.have.string('google-analytics-fake-key-testing-87654321');
        });
    });
})
