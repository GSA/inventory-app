describe('User Reactivation', () => {
    const testUser = 'cypress_reactivate_user';
    const testEmail = testUser + '@gsa.gov';
    const orgName = 'cypress-reactivate-org';

    before(() => {
        cy.create_token();
    });

    beforeEach(() => {
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_organization(orgName);
        cy.login();
    });

    after(() => {
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_organization(orgName);
        cy.revoke_token();
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

                cy.get('#users-without-organizations table tbody tr')
                    .contains(testUser)
                    .should('exist');

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
                    expect(response.status).to.be.oneOf([200, 409]);
                    if (response.body && response.body.error) {
                        expect(response.body.error.message).to.contain('active');
                    }
                });
            });
    });

    it('shows error when reactivating nonexistent user', () => {
        const fakeUserId = 'nonexistent-user-12345';
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
            expect(response.status).to.be.oneOf([404, 409]);
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
