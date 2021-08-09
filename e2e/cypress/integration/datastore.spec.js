describe('Datastore', () => {
    before(() => {
        cy.login('cypress-user', 'cypress-user-password', false);
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');
    })
    beforeEach(() => {
        Cypress.Cookies.preserveOnce('auth_tkt', 'ckan')
    })
    after(() => {
        cy.delete_dataset('test-dataset-1')
        cy.delete_organization('test-organization')
    })

    it('Is installed and available via CKAN API', () => {
        cy.request('/api/3/action/datastore_search?resource_id=_table_metadata')
        .should((response) => {
            expect(response.body).to.have.property('success', true)
        });
    });

    it('Can create datastore resource via API', () => {
        // First create dataset
        cy.fixture('ckan_dataset.json').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).should((response) => {
                expect(response.body).to.have.property('success', true)

                // Create resource with datastore_create api
                var options = {
                    'method': 'POST',
                    'url': '/api/3/action/datastore_create',
                    'headers': {
                        'cache-control': 'no-cache',
                        'content-type': 'application/json'
                    },
                    body: JSON.stringify({
                        "resource": {"package_id": response.body.result.id},
                        "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]
                    })
                };
            
                cy.request(options).should((response) => {
                    expect(response.body).to.have.property('success', true)
                });
            });
        });
    })

    it('Can access datastore API', () => {
        cy.request('/api/action/package_show?id=test-dataset-1').then((response) => {
            expect(response.body).to.have.property('success', true);
            const resource_id = response.body.result.resources[0].id;
            cy.request(`/api/action/datastore_search?resource_id=${resource_id}`).should((response) => {
                expect(response.body).to.have.property('success', true);
                expect(response.body.result).to.have.property('total', 2);
            });
        })
    })

    it('Can delete datastore resource via API', () => {
        cy.request('/api/action/package_show?id=test-dataset-1').then((response) => {
            expect(response.body).to.have.property('success', true);
            const resource_id = response.body.result.resources[0].id;
            // delete resource with datastore_delete api
            var options = {
                'method': 'POST',
                'url': '/api/3/action/datastore_delete',
                'headers': {
                    'cache-control': 'no-cache',
                    'content-type': 'application/json'
                },
                body: JSON.stringify({
                    "resource_id": resource_id,
                })
            };
        
            cy.request(options).should((response) => {
                expect(response.body).to.have.property('success', true)
            });
        });
    })
})
