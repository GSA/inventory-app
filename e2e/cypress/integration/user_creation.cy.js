describe('User Creation Form', () => {
    const testUser = 'cypress_test_user_creation';
    const testEmail = testUser + '@gsa.gov';

    before(() => {
        cy.create_token();
    });

    beforeEach(() => {
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_user('cypress_any_email');
        cy.delete_user('cypress_duplicate');
        cy.delete_user('cypress_clear');
        cy.login();
    });

    after(() => {
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_user('cypress_any_email');
        cy.delete_user('cypress_duplicate');
        cy.delete_user('cypress_clear');
        cy.revoke_token();
    });

    it('renders the user creation form', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form').should('exist');
        cy.get('form#create-user-form input#field-username').should('exist');
        cy.get('form#create-user-form input#field-email').should('exist');
        cy.get('form#create-user-form button[type="submit"]')
            .should('exist')
            .should('contain', 'Add User');
        cy.get('form#create-user-form input[type="password"]').should('not.exist');
    });

    it('creates a user with valid .gov email', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type(testUser);
        cy.get('form#create-user-form input#field-email').clear().type(testEmail);
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.contains('table', testUser).should('exist');
        cy.contains('table', testEmail).should('exist');
    });

    it('accepts any valid email domain', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_any_email');
        cy.get('form#create-user-form input#field-email').clear().type('cypress_any_email@example.com');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.contains('table', 'cypress_any_email').should('exist');
    });

    it('shows error for duplicate username', () => {
        cy.create_user('cypress_duplicate', 'cypress_duplicate@gsa.gov', 'Password123!');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_duplicate');
        cy.get('form#create-user-form input#field-email').clear().type('different@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'login name').should('be.visible');
    });

    it('shows error for empty username', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-email').clear().type('test@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'username').should('be.visible');
    });

    it('shows error for empty email', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('testuser');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'email').should('be.visible');
    });

    it('shows error for invalid email format', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('testuser');
        cy.get('form#create-user-form input#field-email').clear().type('not-an-email');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'email').should('be.visible');
    });

    it('clears form after successful submission', () => {
        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_clear');
        cy.get('form#create-user-form input#field-email').clear().type('cypress_clear@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.get('form#create-user-form input#field-username').should('have.value', '');
        cy.get('form#create-user-form input#field-email').should('have.value', '');
    });
});
