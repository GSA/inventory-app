describe('Main Page', () => {
    
    beforeEach(() => {
        cy.login();
    });

    it('Load main page with configuration', () => {
        cy.visit('/dataset');
        cy.contains('Inventory');
    });

})
