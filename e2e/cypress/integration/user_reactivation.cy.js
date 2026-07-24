describe('User Reactivation', () => {
    const testUser = 'cypress_reactivate_' + Date.now();
    const testEmail = testUser + '@gsa.gov';

    before(() => {
        cy.create_token();
    });

    after(() => {
        cy.delete_user(testUser);
        cy.revoke_token();
    });

    beforeEach(() => {
        cy.login();
    });

    it('shows reactivate button in deleted users section', () => {
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.delete_user(testUser);

        cy.visit('/user/user-org-roles');

        cy.get('#deleted-users').should('exist');
        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('form[action*="reactivate"]').should('exist');
                cy.get('button[type="submit"]')
                    .should('contain', 'Reactivate')
                    .should('be.visible');
            });
    });

    it('reactivates deleted user successfully', () => {
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.delete_user(testUser);

        cy.visit('/user/user-org-roles');

        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.get('#deleted-users table tbody tr').contains(testUser).should('not.exist');

        cy.get('#users-without-organizations table tbody tr')
            .contains(testUser)
            .should('exist');
    });

    it('moves reactivated user to correct section based on organization', () => {
        const orgName = 'cypress-reactivate-org-' + Date.now();
        cy.create_organization(orgName, 'Test org for reactivation');
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.assign_user(orgName, testUser, 'editor');
        cy.delete_user(testUser);

        cy.visit('/user/user-org-roles');

        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.get('#users-with-organizations table tbody tr')
            .contains(testUser)
            .should('exist');

        cy.get('#users-with-organizations table tbody tr')
            .contains(testUser)
            .parents('tr')
            .should('contain', orgName);

        cy.delete_organization(orgName);
    });

    it('shows no reactivate button for active users', () => {
        cy.create_user(testUser, testEmail, 'Password123!');

        cy.visit('/user/user-org-roles');

        cy.get('#users-without-organizations table tbody tr')
            .contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button').contains('Reactivate').should('not.exist');
            });
    });

    it('handles reactivation of already active user gracefully', () => {
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.delete_user(testUser);

        cy.visit('/user/user-org-roles');

        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .find('form[action*="reactivate"]')
            .invoke('attr', 'action')
            .then((actionUrl) => {
                const userId = actionUrl.split('/').pop();

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

                cy.visit('/user/user-org-roles');

                cy.get('#deleted-users table tbody tr')
                    .contains(testUser)
                    .parents('tr')
                    .within(() => {
                        cy.get('button[type="submit"]').contains('Reactivate').click();
                    });

                cy.contains('.alert-error', 'already active').should('be.visible');
            });
    });

    it('shows error when reactivating nonexistent user', () => {
        cy.visit('/user/user-org-roles');

        const fakeUserId = 'nonexistent-user-' + Date.now();
        cy.request({
            method: 'POST',
            url: `/user/reactivate/${fakeUserId}`,
            failOnStatusCode: false,
            headers: {
                'Cookie': document.cookie
            }
        }).then((response) => {
            expect(response.status).to.be.oneOf([404, 302]);
        });
    });

    it('verifies reactivated user can login', () => {
        cy.create_user(testUser, testEmail, 'Password123!');
        cy.delete_user(testUser);

        cy.visit('/user/user-org-roles');

        cy.get('#deleted-users table tbody tr').contains(testUser)
            .parents('tr')
            .within(() => {
                cy.get('button[type="submit"]').contains('Reactivate').click();
            });

        cy.contains('.alert-success', 'reactivated successfully').should('be.visible');

        cy.logout();
        cy.login(testUser, 'Password123!');
        cy.get('.nav-tabs>li>a').should('contain', 'My Organizations');
    });
});
