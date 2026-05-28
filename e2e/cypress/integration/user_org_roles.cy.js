describe('User organization roles', () => {

    beforeEach(() => {
        cy.login();
    });

    it('highlights All Users on the user list page', () => {
        cy.visit('/user/');

        cy.title().should('include', 'All Users');
        cy.get('.secondary .nav-simple .nav-item.active')
            .should('contain', 'All Users')
            .and('not.contain', 'User Roles in Organizations');
        cy.get('.secondary .nav-simple')
            .contains('a', 'User Roles in Organizations')
            .should('have.attr', 'href', '/user/user-org-roles');
    });

    it('renders and highlights User Roles in Organizations', () => {
        cy.visit('/user/user-org-roles');

        cy.title().should('include', 'User Roles in Organizations');
        cy.get('.breadcrumb .active')
            .should('contain', 'User Roles in Organizations');
        cy.get('.secondary .nav-simple .nav-item.active')
            .should('contain', 'User Roles in Organizations')
            .and('not.contain', 'All Users');
        cy.get('article.user-org-roles')
            .should('contain', 'User Roles in Organizations');
        cy.get('article.user-org-roles table.table-header')
            .should('exist');
        cy.get('article.user-org-roles .user-org-roles-sort')
            .should('exist');
    });

});
