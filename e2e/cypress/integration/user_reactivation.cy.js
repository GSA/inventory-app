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

    it('moves reactivated user to correct section based on organization', () => {
        cy.log('>>> TEST START: moves reactivated user to correct section based on organization');
        cy.task('log', `>>> TEST: Creating organization ${orgName}`);
        cy.create_organization(orgName, 'Test org for reactivation');

        cy.task('log', `>>> TEST: Creating user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', `>>> TEST: Assigning ${testUser} to ${orgName} as editor`);
        cy.assign_user(orgName, testUser, 'editor');

        cy.task('log', `>>> TEST: Deleting user ${testUser}`);
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Reactivating ${testUser} from deleted section`);
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.task('log', '>>> TEST: Checking for success message');
        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.task('log', `>>> TEST: Verifying ${testUser} appears in users-with-organizations section`);
        cy.get('#users-with-organizations table tbody tr')
            .contains(testUser)
            .should('exist');

        cy.task('log', `>>> TEST: Verifying ${testUser} row contains organization ${orgName}`);
        cy.get('#users-with-organizations table tbody tr')
            .contains(testUser)
            .parents('tr')
            .should('contain', orgName);
        cy.task('log', `>>> TEST COMPLETE: moves reactivated user to correct section - User ${testUser} in correct section with org ${orgName}`);
    });

    it('shows no reactivate button for active users', () => {
        cy.log('>>> TEST START: shows no reactivate button for active users');
        cy.task('log', `>>> TEST: Creating active user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Finding ${testUser} in users-without-organizations section`);
        cy.get('#users-without-organizations table tbody tr')
            .contains(testUser)
            .parents('tr')
            .within(() => {
                cy.task('log', '>>> TEST: Verifying no Reactivate button exists for active user');
                cy.get('button').contains('Reactivate').should('not.exist');
            });
        cy.task('log', '>>> TEST COMPLETE: shows no reactivate button for active users - No button found (correct)');
    });

    it('handles reactivation of already active user gracefully', () => {
        cy.log('>>> TEST START: handles reactivation of already active user gracefully');
        cy.task('log', `>>> TEST: Creating user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', `>>> TEST: Deleting user ${testUser}`);
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Finding ${testUser} in deleted section and extracting user ID`);
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .find('form[action*="reactivate"]')
            .invoke('attr', 'action')
            .then((actionUrl) => {
                const userId = actionUrl.split('/').pop();
                cy.task('log', `>>> TEST: Extracted user ID: ${userId}`);

                cy.task('log', `>>> TEST: Reactivating user ${userId} via API (first time)`);
                cy.request({
                    method: 'POST',
                    url: '/api/3/action/reactivate_user',
                    headers: {
                        'X-CKAN-API-Key': Cypress.env('token_data').api_token,
                    },
                    body: {
                        id: userId
                    }
                });

                cy.task('log', '>>> TEST: Revisiting page to verify user is active');
                cy.visit('/user/user-org-roles');

                cy.task('log', `>>> TEST: Verifying ${testUser} appears in users-without-organizations (active)`);
                cy.get('#users-without-organizations table tbody tr')
                    .contains(testUser)
                    .should('exist');

                cy.task('log', `>>> TEST: Attempting to reactivate already-active user ${userId} (should fail gracefully)`);
                cy.request({
                    method: 'POST',
                    url: '/api/3/action/reactivate_user',
                    failOnStatusCode: false,
                    headers: {
                        'X-CKAN-API-Key': Cypress.env('token_data').api_token,
                    },
                    body: {
                        id: userId
                    }
                }).then((response) => {
                    cy.task('log', `>>> TEST: Response status: ${response.status}`);
                    cy.task('log', `>>> TEST: Response body: ${JSON.stringify(response.body)}`);
                    expect(response.status).to.be.oneOf([200, 409]);
                    if (response.body && response.body.error) {
                        cy.task('log', `>>> TEST: Error message contains 'active': ${response.body.error.message}`);
                        expect(response.body.error.message).to.contain('active');
                    }
                });
                cy.task('log', '>>> TEST COMPLETE: handles reactivation of already active user gracefully');
            });
    });

    it('shows error when reactivating nonexistent user', () => {
        cy.log('>>> TEST START: shows error when reactivating nonexistent user');
        const fakeUserId = 'nonexistent-user-12345';
        cy.task('log', `>>> TEST: Attempting to reactivate nonexistent user: ${fakeUserId}`);

        cy.request({
            method: 'POST',
            url: '/api/3/action/reactivate_user',
            failOnStatusCode: false,
            headers: {
                'X-CKAN-API-Key': Cypress.env('token_data').api_token,
            },
            body: {
                id: fakeUserId
            }
        }).then((response) => {
            cy.task('log', `>>> TEST: Response status: ${response.status}`);
            cy.task('log', `>>> TEST: Response body: ${JSON.stringify(response.body)}`);
            expect(response.status).to.be.oneOf([404, 409]);
            cy.task('log', `>>> TEST COMPLETE: shows error when reactivating nonexistent user - Received expected error status ${response.status}`);
        });
    });

    it('verifies reactivated user can login', () => {
        cy.log('>>> TEST START: verifies reactivated user can login');
        cy.task('log', `>>> TEST: Creating user ${testUser}`);
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.task('log', `>>> TEST: Deleting user ${testUser}`);
        cy.delete_user(testUser);

        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', `>>> TEST: Reactivating ${testUser} via UI`);
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.task('log', '>>> TEST: Checking for success message');
        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.task('log', `>>> TEST: Logging out admin and attempting to login as ${testUser}`);
        cy.logout();
        cy.login(testUser, 'Password123!');

        cy.task('log', '>>> TEST: Verifying user can see My Organizations tab');
        cy.get('.nav-tabs>li>a').should('contain', 'My Organizations');
        cy.task('log', `>>> TEST COMPLETE: verifies reactivated user can login - User ${testUser} logged in successfully`);
    });
});
