import Chance from 'chance';
const chance = new Chance();
const userPassword = chance.string({ length: 8 });

describe('Dataset', () => {

    before(() => {
        cy.create_token();
        cy.logout();
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');
        cy.fixture('ckan_dataset.json').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset)
        });
    });

    after(() => {
        cy.delete_dataset('test-dataset-1');
        cy.delete_organization('test-organization');
        cy.revoke_token();
    });

    it('Sysadmin can create an editor', () => {
        cy.log('USER_PERM: Starting create editor test');
        cy.log('USER_PERM: User password: ' + userPassword);
        cy.create_user('an_editor', 'editor@local.localhost', userPassword);
        cy.log('USER_PERM: User created: an_editor');
        cy.assign_user('test-organization', 'an_editor', 'editor');
        cy.log('USER_PERM: User assigned to test-organization as editor');
        cy.logout();
        cy.log('USER_PERM: Logged out');
    });

    it('Editor can login and edit dataset', () => {
        cy.log('USER_PERM: Starting editor login and edit test');
        cy.log('USER_PERM: Logging in as an_editor');
        cy.login('an_editor', userPassword);
        cy.log('USER_PERM: Login completed, checking for username');

        // Verify login succeeded by checking for username
        cy.get('body').then(($body) => {
            const bodyText = $body.text();
            const hasUsername = bodyText.includes('an_editor');
            cy.log('USER_PERM: Body contains username: ' + hasUsername);
            if (!hasUsername) {
                cy.log('USER_PERM: ERROR - Username not found. First 200 chars of page: ' + bodyText.substring(0, 200));
            }
        });
        cy.contains('an_editor', { timeout: 10000 }).should('be.visible');

        cy.log('USER_PERM: Visiting dataset page');
        cy.visit('/dataset/test-dataset-1');

        // Check what buttons/links are available
        cy.get('body').then(($body) => {
            const allButtons = $body.find('button, a').map((i, el) => $(el).text().trim()).get().filter(t => t.length > 0 && t.length < 50);
            cy.log('USER_PERM: Available buttons/links: ' + allButtons.slice(0, 10).join(', '));
        });

        cy.log('USER_PERM: Looking for Edit button');
        cy.contains('Edit', { timeout: 10000 }).should('be.visible').then(($btn) => {
            cy.log('USER_PERM: Found Edit button, clicking...');
        }).click();

        cy.log('USER_PERM: Clicked Edit button, checking URL');
        cy.url({ timeout: 10000 }).then((url) => {
            cy.log('USER_PERM: Current URL: ' + url);
            expect(url, 'URL should contain edit-new path after clicking Edit').to.include('/dataset/edit-new/test-dataset-1');
        });

        cy.log('USER_PERM: Looking for Save and Continue button');
        cy.contains('Save and Continue', { timeout: 10000 }).should('be.visible').then(($btn) => {
            cy.log('USER_PERM: Found Save and Continue button, clicking...');
        }).click();

        cy.log('USER_PERM: Clicked Save and Continue, checking URL');
        cy.url({ timeout: 10000 }).then((url) => {
            cy.log('USER_PERM: URL after Save: ' + url);
            expect(url, 'URL should still be on edit page after save').to.include('/dataset/edit-new/test-dataset-1');
        });

        cy.log('USER_PERM: Logging out');
        cy.logout();
        cy.log('USER_PERM: Logged out successfully');
    });

    it('Sysadmin can delete an editor', () => {
        cy.log('USER_PERM: Starting delete editor test');
        cy.delete_user('an_editor');
        cy.log('USER_PERM: User an_editor deleted');
        cy.logout();
        cy.log('USER_PERM: Logged out');
    });

})
