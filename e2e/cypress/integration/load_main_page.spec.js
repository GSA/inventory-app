it('Load main page', () => {
    cy.visit('/dataset')
    cy.contains('Inventory')
});