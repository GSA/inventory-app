describe('Organization', () => {
    before(() => {
        cy.login('cypress-user', 'cypress-user-password', false)
    })
    beforeEach(() => {
        Cypress.Cookies.preserveOnce('auth_tkt', 'ckan')
    })
    after(() => {
        cy.delete_organization('cypress-test-org')
    })
    it('Create Organization', () => {
        cy.visit('/organization')
        cy.get('a[class="btn btn-primary"]').click()
        cy.create_organization_ui('cypress-test-org', 'cypress test description')
        cy.screenshot()
        cy.visit('/organization/cypress-test-org')
        cy.screenshot()
    })
    it('Contains Organization Information', () => {
        cy.contains('No datasets found')
        cy.contains('cypress test description')
        cy.contains('0')
        cy.get('a[href="/organization/cypress-test-org"]')
    })
    it('Edit Organization Description', () => {
        cy.visit('/organization/edit/cypress-test-org')
        //cy.get('#field-url').then($field_url => {
        //    if($field_url.is(':visible')) {
        //        $field_url.type(orgName)
        //    }
        //})
        //cy.get('a[class="btn btn-primary"]').click()
        cy.get('#field-description').clear()
        cy.get('#field-description').type('the new description')
        cy.screenshot()
        // cy.get('button[type=submit]').click()
        cy.get('button[name=save]').click()
    })
})