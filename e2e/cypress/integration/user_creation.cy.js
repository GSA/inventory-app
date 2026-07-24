describe('User Creation Form', () => {
    const testUser = 'cypress_test_user_' + Date.now();
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
        cy.visit('/user/user-org-roles');
    });

    it('renders the user creation form', () => {
        cy.get('form#create-user-form').should('exist');
        cy.get('form#create-user-form input#field-username').should('exist');
        cy.get('form#create-user-form input#field-email').should('exist');
        cy.get('form#create-user-form button[type="submit"]')
            .should('exist')
            .should('contain', 'Add User');
        cy.get('form#create-user-form input[type="password"]').should('not.exist');
    });

    it('creates a user with valid .gov email', () => {
        cy.get('form#create-user-form input#field-username').type(testUser);
        cy.get('form#create-user-form input#field-email').type(testEmail);
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.contains('table', testUser).should('exist');
        cy.contains('table', testEmail).should('exist');
    });

    it('accepts any valid email domain', () => {
        const testUser = 'cypress_any_email_' + Date.now();
        cy.get('form#create-user-form input#field-username').type(testUser);
        cy.get('form#create-user-form input#field-email').type(testUser + '@example.com');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.contains('table', testUser).should('exist');

        cy.delete_user(testUser);
    });

    it('shows error for duplicate username', () => {
        const duplicateUser = 'cypress_duplicate_' + Date.now();
        cy.create_user(duplicateUser, duplicateUser + '@gsa.gov', 'Password123!');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').type(duplicateUser);
        cy.get('form#create-user-form input#field-email').type('different@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'login name').should('be.visible');

        cy.delete_user(duplicateUser);
    });

    it('shows error for empty username', () => {
        cy.get('form#create-user-form input#field-email').type('test@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'username').should('be.visible');
    });

    it('shows error for empty email', () => {
        cy.get('form#create-user-form input#field-username').type('testuser');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'email').should('be.visible');
    });

    it('shows error for invalid email format', () => {
        cy.get('form#create-user-form input#field-username').type('testuser');
        cy.get('form#create-user-form input#field-email').type('not-an-email');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-error', 'email').should('be.visible');
    });

    it('clears form after successful submission', () => {
        const clearTestUser = 'cypress_clear_' + Date.now();
        cy.get('form#create-user-form input#field-username').type(clearTestUser);
        cy.get('form#create-user-form input#field-email').type(clearTestUser + '@gsa.gov');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.contains('.alert-success', 'User created successfully').should('be.visible');
        cy.get('form#create-user-form input#field-username').should('have.value', '');
        cy.get('form#create-user-form input#field-email').should('have.value', '');

        cy.delete_user(clearTestUser);
    });
});
