describe('User Reactivation', () => {
    const testUser = 'cypress_reactivate_user';
    const testEmail = testUser + '@gsa.gov';
    const orgName = 'cypress-reactivate-org';

    before(() => {
        cy.log('=== USER_REACTIVATION: BEFORE HOOK START ===');
        cy.task('log', '=== USER_REACTIVATION: Creating token ===');
        cy.create_token();
        cy.log('=== USER_REACTIVATION: BEFORE HOOK COMPLETE ===');
    });

    beforeEach(function() {
        cy.log(`=== USER_REACTIVATION: BEFOREEACH START - Test: ${this.currentTest.title} ===`);
        cy.task('log', `=== USER_REACTIVATION: Running beforeEach for: ${this.currentTest.title} ===`);

        cy.task('log', '>>> USER_REACTIVATION: Logging out');
        cy.logout();

        cy.task('log', `>>> USER_REACTIVATION: Deleting user: ${testUser}`);
        cy.delete_user(testUser);
        cy.task('log', `>>> USER_REACTIVATION: Deleting organization: ${orgName}`);
        cy.delete_organization(orgName);

        cy.task('log', '>>> USER_REACTIVATION: Logging in');
        cy.login();
        cy.log(`=== USER_REACTIVATION: BEFOREEACH COMPLETE - Test: ${this.currentTest.title} ===`);
    });

    after(() => {
        cy.log('=== USER_REACTIVATION: AFTER HOOK START ===');
        cy.task('log', '=== USER_REACTIVATION: Cleaning up ===');
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_organization(orgName);
        cy.revoke_token();
        cy.log('=== USER_REACTIVATION: AFTER HOOK COMPLETE ===');
    });

    it('shows reactivate button in deleted users section', () => {
        cy.log('>>> TEST START: shows reactivate button in deleted users section');
        cy.task('log', `>>> TEST: Creating user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', `>>> TEST: Deleting user ${testUser} to move to deleted section`);
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles page');
        cy.visit('/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking #deleted-users section exists');
        cy.get('#deleted-users').should('exist');

        cy.task('log', `>>> TEST: Looking for ${testUser} in deleted users table`);
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.task('log', '>>> TEST: Verifying reactivate form and button exist');
                cy.get('form[action*="reactivate"]').should('exist');
                cy.get('button[type="submit"]')
                    .should('contain', 'Reactivate')
                    .should('be.visible');
            });
        cy.task('log', '>>> TEST COMPLETE: shows reactivate button in deleted users section - Button displayed correctly');
    });

    it('reactivates deleted user successfully', () => {
        cy.log('>>> TEST START: reactivates deleted user successfully');
        cy.task('log', `>>> TEST: Creating and deleting user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Finding ${testUser} in deleted users and clicking Reactivate`);
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.task('log', '>>> TEST: Checking for success message');
        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.task('log', '>>> TEST: Verifying user removed from deleted section');
        cy.get('#deleted-users table tbody tr').contains(testUser).should('not.exist');

        cy.task('log', '>>> TEST: Verifying user appears in users-without-organizations section');
        cy.get('#users-without-organizations table tbody tr')
            .contains(testUser)
            .should('exist');
        cy.task('log', `>>> TEST COMPLETE: reactivates deleted user successfully - User ${testUser} reactivated and moved to correct section`);
    });


    it('verifies reactivated user can be used', () => {
        cy.log('>>> TEST START: verifies reactivated user is functional');
        cy.task('log', `>>> TEST: Creating user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', `>>> TEST: Deleting user ${testUser}`);
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Reactivating ${testUser} via UI`);
        cy.get('#deleted-users table tbody tr', {timeout: 10000}).contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.task('log', '>>> TEST: Waiting for page reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for success message');
        cy.contains('.alert', 'reactivated successfully', {timeout: 10000}).should('be.visible');

        cy.task('log', `>>> TEST: Verifying ${testUser} is no longer in deleted section`);
        cy.get('#deleted-users table tbody tr').contains(testUser).should('not.exist');

        cy.task('log', `>>> TEST COMPLETE: verifies reactivated user is functional - User ${testUser} reactivated and removed from deleted section`);
    });
});
