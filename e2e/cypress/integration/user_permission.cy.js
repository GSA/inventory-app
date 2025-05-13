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
        cy.create_user('an_editor', 'editor@local.localhost', userPassword);
        cy.assign_user('test-organization', 'an_editor', 'editor');
        cy.logout();
    });

    it('Editor can login and edit dataset', () => {
        cy.login('an_editor', userPassword);
        cy.contains('an_editor');
        cy.visit('/dataset/test-dataset-1');
        cy.visit('/dataset/edit-new/test-dataset-1');
        cy.contains('Save and Continue').click();
        cy.logout();
    });

    it('Sysadmin can delete an editor', () => {
        cy.delete_user('an_editor');
        cy.logout();
    });

})
