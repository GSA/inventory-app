describe('Login', () => {
    
    it('Invalid user login attempt', () => {
        cy.login('not-user', 'not-password', true)
        cy.contains('Not authorized to see this page')
    });

    it('Valid login attempt', () => {
        cy.login()
        cy.get('.nav-tabs>li>a').should('contain', 'My Organizations')
    })

})
