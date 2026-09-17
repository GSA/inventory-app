describe('User organization roles', () => {
    const orgA = 'cypress-user-org-roles-a';
    const orgB = 'cypress-user-org-roles-b';
    const userA = 'gsa_admin';
    const userB = 'doi_admin';
    const userPassword = 'Password123!';

    before(() => {
        cy.create_token();
        cy.delete_user(userA);
        cy.delete_user(userB);
        cy.delete_organization(orgA);
        cy.delete_organization(orgB);
        cy.create_organization(orgA, 'Cypress user org roles A');
        cy.create_organization(orgB, 'Cypress user org roles B');
        cy.create_user(userA, 'gsa_admin@example.com', userPassword);
        cy.create_user(userB, 'doi_admin@example.com', userPassword);
        cy.assign_user(orgA, userA, 'admin');
        cy.assign_user(orgB, userA, 'editor');
        cy.assign_user(orgB, userB, 'member');
    });

    after(() => {
        cy.delete_user(userA);
        cy.delete_user(userB);
        cy.delete_organization(orgA);
        cy.delete_organization(orgB);
        cy.revoke_token();
    });

    beforeEach(() => {
        cy.login();
    });

    it('links to user organization roles from the account header', () => {
        cy.visit('/');

        cy.get('.account-masthead')
            .find('a[title="User Roles in Organizations"]')
            .should('have.attr', 'href', '/user/user-org-roles')
            .find('i')
            .should('have.class', 'fa-user-group');
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
        cy.get('#deleted-users').should('not.exist');
        cy.get('.user-org-roles-summary').should('not.contain', 'Deleted Users');
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

        cy.get('#users-with-organizations table[data-sortable-table]')
            .within(() => {
                cy.get('tbody tr').then(($rows) => {
                    const userRows = [...$rows].filter((row) =>
                        row.cells[0].innerText.trim() === userA
                    );
                    expect(userRows).to.have.length(1);
                    expect(userRows[0].cells[3].innerText).to.contain(orgA);
                    expect(userRows[0].cells[3].innerText).to.contain(orgB);
                    expect(userRows[0].cells[3].headers).to.equal(
                        'users-with-organizations-organization-heading ' +
                        'users-with-organizations-role-heading'
                    );
                    cy.wrap(userRows[0])
                        .find('a.user-org-roles-delete')
                        .should('have.attr', 'aria-label', 'Delete user')
                        .and('have.css', 'float', 'right')
                        .find('i')
                        .should('have.class', 'fa-user-xmark');
                    const memberships = userRows[0].querySelectorAll(
                        '.user-org-roles-membership'
                    );
                    expect(memberships).to.have.length(2);
                    expect(memberships[0].innerText).to.contain(orgA);
                    expect(memberships[0].innerText).to.contain('admin');
                    expect(memberships[0].querySelector('a').innerText)
                        .to.contain('Organization:');
                    expect(memberships[0].children[1].innerText)
                        .to.contain('Role:');
                    expect(memberships[1].innerText).to.contain(orgB);
                    expect(memberships[1].innerText).to.contain('editor');
                    const membershipsCell = userRows[0].cells[3];
                    const dividerStyle = membershipsCell.ownerDocument.defaultView
                        .getComputedStyle(membershipsCell, '::after');
                    expect(dividerStyle.top).to.equal('0px');
                    expect(dividerStyle.bottom).to.equal('0px');
                    expect(dividerStyle.right).to.equal('80px');
                    expect(dividerStyle.borderLeftWidth).to.equal('1px');
                });
                cy.contains('.user-org-roles-membership > span', 'member')
                    .should('have.css', 'white-space', 'nowrap');
                cy.contains('th', 'Organization')
                    .should('have.attr', 'data-sort-field', 'organization');
                cy.contains('th', 'Role')
                    .should('have.attr', 'data-sort-field', 'role');

                cy.contains('button', 'Organization').click();
                cy.get('tbody tr').then(($rows) => {
                    const rowTexts = [...$rows].map((row) => row.innerText);
                    expect(rowTexts.findIndex((text) => text.includes(userA)))
                        .to.be.lessThan(
                            rowTexts.findIndex((text) => text.includes(userB))
                        );
                });

                cy.contains('button', 'Organization').click();
                cy.get('tbody tr').then(($rows) => {
                    const rowTexts = [...$rows].map((row) => row.innerText);
                    expect(rowTexts.findIndex((text) => text.includes(userB)))
                        .to.be.lessThan(
                            rowTexts.findIndex((text) => text.includes(userA))
                        );
                });

                cy.contains('button', 'Role').click();
                cy.get('tbody tr').then(($rows) => {
                    const rowTexts = [...$rows].map((row) => row.innerText);
                    expect(rowTexts.findIndex((text) => text.includes(userA)))
                        .to.be.lessThan(
                            rowTexts.findIndex((text) => text.includes(userB))
                        );
                });

                cy.contains('button', 'Role').click();
                cy.get('tbody tr').then(($rows) => {
                    const rowTexts = [...$rows].map((row) => row.innerText);
                    expect(rowTexts.findIndex((text) => text.includes(userB)))
                        .to.be.lessThan(
                            rowTexts.findIndex((text) => text.includes(userA))
                        );
                });
            });
    });

    it('opens Deleted Users from the third sidebar tab', () => {
        cy.visit('/user/user-org-roles');
        cy.get('.secondary .nav-simple a[href="/user/deleted-users"]')
            .contains('Deleted Users')
            .should('have.attr', 'href', '/user/deleted-users')
            .click({force: true});
        cy.title().should('include', 'Deleted Users');
        cy.get('.breadcrumb .active').should('contain', 'Deleted Users');
        cy.get('.secondary .nav-simple .nav-item.active')
            .should('have.length', 1)
            .and('contain', 'Deleted Users');
        cy.get('#deleted-users table[data-sortable-table]').should('exist');
        cy.get('#deleted-users thead').should('not.contain', 'Actions');
        cy.get('#sysadmins, #users-with-organizations, #users-without-organizations, #create-user-form')
            .should('not.exist');
    });

});
