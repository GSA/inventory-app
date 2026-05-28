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
        cy.get('.user-org-roles-summary')
            .contains('a', 'Sysadmins')
            .should('have.attr', 'href', '#sysadmins');
        cy.get('.user-org-roles-summary')
            .contains('a', 'Users with organizations')
            .should('have.attr', 'href', '#users-with-organizations');
        cy.get('.user-org-roles-summary')
            .contains('a', 'Users without organizations')
            .should('have.attr', 'href', '#users-without-organizations');
        cy.get('.user-org-roles-summary')
            .contains('a', 'Deleted Users')
            .should('have.attr', 'href', '#deleted-users');
        cy.get('article.user-org-roles table.table-header')
            .should('exist');
        cy.get('article.user-org-roles .user-org-roles-section')
            .each(($section) => {
                const sectionId = $section.attr('id');

                cy.wrap($section)
                    .find('h2 span')
                    .invoke('text')
                    .then((text) => {
                        const match = text.match(/^(\d+)\s+rows$/);
                        expect(match, `row count for ${sectionId}`).to.not.be.null;

                        const rowCount = Number(match[1]);
                        cy.get(`.user-org-roles-summary a[href="#${sectionId}"]`)
                            .should('contain', `${rowCount} rows`);

                        cy.wrap($section)
                            .find('tbody tr')
                            .then(($rows) => {
                                if (rowCount === 0) {
                                    expect($rows).to.have.length(1);
                                    expect($rows.eq(0)).to.contain('No users');
                                } else {
                                    expect($rows).to.have.length(rowCount);
                                }
                            });
                    });
                cy.wrap($section)
                    .contains('a', 'Go to top')
                    .should('have.attr', 'href', '#user-org-roles-top');
            });
        cy.get('article.user-org-roles .user-org-roles-sort')
            .should('exist');
    });

});
