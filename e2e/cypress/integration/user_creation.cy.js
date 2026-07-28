describe('User Creation Form', () => {
    const testUser = 'cypress_test_user_creation';
    const testEmail = testUser + '@gsa.gov';

    before(() => {
        cy.log('=== USER_CREATION: BEFORE HOOK START ===');
        cy.task('log', '=== USER_CREATION: Creating token ===');
        cy.create_token();
        cy.log('=== USER_CREATION: BEFORE HOOK COMPLETE ===');
    });

    beforeEach(function() {
        cy.log(`=== USER_CREATION: BEFOREEACH START - Test: ${this.currentTest.title} ===`);
        cy.task('log', `=== USER_CREATION: Running beforeEach for: ${this.currentTest.title} ===`);

        cy.task('log', '>>> USER_CREATION: Logging out');
        cy.logout();

        cy.task('log', `>>> USER_CREATION: Deleting user: ${testUser}`);
        cy.delete_user(testUser);
        cy.task('log', '>>> USER_CREATION: Deleting user: cypress_any_email');
        cy.delete_user('cypress_any_email');
        cy.task('log', '>>> USER_CREATION: Deleting user: cypress_duplicate');
        cy.delete_user('cypress_duplicate');
        cy.task('log', '>>> USER_CREATION: Deleting user: cypress_clear');
        cy.delete_user('cypress_clear');

        cy.task('log', '>>> USER_CREATION: Logging in');
        cy.login();
        cy.log(`=== USER_CREATION: BEFOREEACH COMPLETE - Test: ${this.currentTest.title} ===`);
    });

    after(() => {
        cy.log('=== USER_CREATION: AFTER HOOK START ===');
        cy.task('log', '=== USER_CREATION: Cleaning up users ===');
        cy.logout();
        cy.delete_user(testUser);
        cy.delete_user('cypress_any_email');
        cy.delete_user('cypress_duplicate');
        cy.delete_user('cypress_clear');
        cy.revoke_token();
        cy.log('=== USER_CREATION: AFTER HOOK COMPLETE ===');
    });

    it('renders the user creation form', () => {
        cy.log('>>> TEST START: renders the user creation form');
        cy.task('log', '>>> TEST: Visiting /user/user-org-roles');
        cy.visit('/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking form exists');
        cy.get('form#create-user-form').should('exist');
        cy.get('form#create-user-form input#field-username').should('exist');
        cy.get('form#create-user-form input#field-email').should('exist');
        cy.get('form#create-user-form button[type="submit"]')
            .should('exist')
            .should('contain', 'Add User');
        cy.get('form#create-user-form input[type="password"]').should('not.exist');
        cy.task('log', '>>> TEST COMPLETE: renders the user creation form');
    });

    it('creates a user with valid .gov email', () => {
        cy.log('>>> TEST START: creates a user with valid .gov email');
        cy.task('log', `>>> TEST: Creating user ${testUser} with email ${testEmail}`);

        cy.visit('/user/user-org-roles');
        cy.task('log', '>>> TEST: Filling out form');
        cy.get('form#create-user-form input#field-username').clear().type(testUser);
        cy.get('form#create-user-form input#field-email').clear().type(testEmail);

        cy.task('log', '>>> TEST: Submitting form');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page to reload after form submission');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for success message (flash message after redirect)');
        cy.get('.alert', {timeout: 10000}).should('exist').then(($alert) => {
            cy.task('log', `>>> TEST: Found alert element with classes: ${$alert.attr('class')}`);
            cy.task('log', `>>> TEST: Alert text content: ${$alert.text()}`);
        });
        cy.contains('.alert', 'created successfully', {timeout: 10000}).should('be.visible');

        cy.task('log', '>>> TEST: Verifying user appears in table');
        cy.contains('table', testUser).should('exist');
        cy.contains('table', testEmail).should('exist');
        cy.task('log', `>>> TEST COMPLETE: creates a user with valid .gov email - User ${testUser} created successfully`);
    });

    it('accepts any valid email domain', () => {
        cy.log('>>> TEST START: accepts any valid email domain');
        cy.task('log', '>>> TEST: Creating user cypress_any_email with @example.com email');

        cy.visit('/user/user-org-roles');
        cy.task('log', '>>> TEST: Filling out form');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_any_email');
        cy.get('form#create-user-form input#field-email').clear().type('cypress_any_email@example.com');

        cy.task('log', '>>> TEST: Submitting form');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page to reload after form submission');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for success message');
        cy.contains('.alert', 'created successfully', {timeout: 10000}).should('be.visible');
        cy.contains('table', 'cypress_any_email').should('exist');
        cy.task('log', '>>> TEST COMPLETE: accepts any valid email domain - User cypress_any_email created successfully');
    });

    it('shows error for duplicate username', () => {
        cy.log('>>> TEST START: shows error for duplicate username');
        cy.task('log', '>>> TEST: Creating initial cypress_duplicate user via API');
        cy.create_user('cypress_duplicate', 'cypress_duplicate@gsa.gov', 'Password123!');
        cy.task('log', '>>> TEST: Initial user created, now attempting to create duplicate');

        cy.visit('/user/user-org-roles');
        cy.task('log', '>>> TEST: Filling form with duplicate username');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_duplicate');
        cy.get('form#create-user-form input#field-email').clear().type('different@gsa.gov');

        cy.task('log', '>>> TEST: Submitting form with duplicate username');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page to reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for error message about login name');
        cy.get('.alert', {timeout: 10000}).should('exist').then(($alert) => {
            cy.task('log', `>>> TEST: Found alert with text: ${$alert.text()}`);
        });
        cy.contains('.alert', 'login name', {timeout: 10000}).should('be.visible');
        cy.task('log', '>>> TEST COMPLETE: shows error for duplicate username - Error message displayed correctly');
    });

    it('shows error for empty username', () => {
        cy.log('>>> TEST START: shows error for empty username');
        cy.task('log', '>>> TEST: Submitting form with empty username');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-email').clear().type('test@gsa.gov');

        cy.task('log', '>>> TEST: Clicking submit without username');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for username error message');
        cy.contains('.alert', 'username', {timeout: 10000}).should('be.visible');
        cy.task('log', '>>> TEST COMPLETE: shows error for empty username - Error displayed correctly');
    });

    it('shows error for empty email', () => {
        cy.log('>>> TEST START: shows error for empty email');
        cy.task('log', '>>> TEST: Submitting form with empty email');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('testuser');

        cy.task('log', '>>> TEST: Clicking submit without email');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for email error message');
        cy.contains('.alert', 'email', {timeout: 10000}).should('be.visible');
        cy.task('log', '>>> TEST COMPLETE: shows error for empty email - Error displayed correctly');
    });

    it('shows error for invalid email format', () => {
        cy.log('>>> TEST START: shows error for invalid email format');
        cy.task('log', '>>> TEST: Submitting form with invalid email format');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('testuser');
        cy.get('form#create-user-form input#field-email').clear().type('not-an-email');

        cy.task('log', '>>> TEST: Clicking submit with invalid email');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Checking for email format error message');
        cy.contains('.alert', 'email', {timeout: 10000}).should('be.visible');
        cy.task('log', '>>> TEST COMPLETE: shows error for invalid email format - Error displayed correctly');
    });

    it('clears form after successful submission', () => {
        cy.log('>>> TEST START: clears form after successful submission');
        cy.task('log', '>>> TEST: Creating user cypress_clear to verify form clears');

        cy.visit('/user/user-org-roles');
        cy.get('form#create-user-form input#field-username').clear().type('cypress_clear');
        cy.get('form#create-user-form input#field-email').clear().type('cypress_clear@gsa.gov');

        cy.task('log', '>>> TEST: Submitting form');
        cy.get('form#create-user-form button[type="submit"]').click();

        cy.task('log', '>>> TEST: Waiting for page reload');
        cy.url().should('include', '/user/user-org-roles');

        cy.task('log', '>>> TEST: Verifying success message');
        cy.contains('.alert', 'created successfully', {timeout: 10000}).should('be.visible');

        cy.task('log', '>>> TEST: Checking if form fields are cleared');
        cy.get('form#create-user-form input#field-username').should('have.value', '');
        cy.get('form#create-user-form input#field-email').should('have.value', '');
        cy.task('log', '>>> TEST COMPLETE: clears form after successful submission - Form cleared successfully');
    });
});
