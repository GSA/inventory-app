describe('Login', () => {
    
    it('Invalid user login attempt', () => {
        cy.login('not-user', 'not-password', true)
        cy.contains('Login Failed.')
    });

    it('Valid login attempt', () => {
        cy.login()
        cy.get('.nav-tabs>li>a').should('contain', 'My Organizations')
    })

})
