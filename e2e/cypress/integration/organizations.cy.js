describe('Organization', () => {
    before(() => {
        cy.create_token();
    })

    beforeEach(() => {
        cy.login()
    })

    after(() => {
        cy.delete_organization('cypress-test-org')
        cy.revoke_token()
    })

    it('Create Organization', () => {
        cy.visit('/organization')
        cy.get('a[class="btn btn-primary"]').click()
        cy.create_organization_ui('cypress-test-org', 'cypress test description')
    })

    it('Contains Organization Information', () => {
        cy.visit('/organization/cypress-test-org')
        cy.contains('No datasets found')
        cy.contains('cypress test description')
        cy.contains('0')
        cy.get('a[href="/organization/cypress-test-org"]')
    })
    
    it('Edit Organization Description', () => {
        cy.visit('/organization/edit/cypress-test-org')

        cy.get('#field-description').clear()
        cy.get('#field-description').type('the new description')
        cy.get('button[name=save]').click()
    })
})
