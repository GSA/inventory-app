describe('Datastore', () => {

    before(() => {
        cy.create_token();
        cy.logout();
        cy.delete_organization('test-organization');
        cy.create_organization('test-organization', 'Test organization');
    })

    after(() => {
        cy.delete_dataset('test-dataset-1')
        cy.delete_organization('test-organization')
        cy.revoke_token();
    })

    it('Is installed and available via CKAN API', () => {
        const token_data = Cypress.env('token_data');
        cy.request({
            method: 'GET',
            url: '/api/3/action/datastore_search?resource_id=_table_metadata',
            headers: {
                'Authorization': token_data.api_token
            }
        }).should((response) => {
            expect(response.body).to.have.property('success', true)
        });
    });

    it('Can create datastore resource via API', () => {
        const token_data = Cypress.env('token_data');
        // First create dataset
        cy.fixture('ckan_dataset.json').then((ckan_dataset) => {
            cy.create_dataset(ckan_dataset).then((response) => {
                expect(response.body).to.have.property('success', true)

                // Create resource with datastore_create api
                var options = {
                    'method': 'POST',
                    'url': '/api/3/action/datastore_create',
                    'headers': {
                        'cache-control': 'no-cache',
                        'content-type': 'application/json',
                        'Authorization': token_data.api_token
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
        const token_data = Cypress.env('token_data');
        cy.request({
            method: 'GET',
            url: '/api/action/package_show?id=test-dataset-1',
            headers: {
                'Authorization': token_data.api_token
            }
        }).then((response) => {
            expect(response.body).to.have.property('success', true);
            const resource_id = response.body.result.resources[0].id;
            cy.request({
                method: 'GET',
                url: `/api/action/datastore_search?resource_id=${resource_id}`,
                headers: {
                    'Authorization': token_data.api_token
                }
            }).should((response) => {
                expect(response.body).to.have.property('success', true);
                expect(response.body.result).to.have.property('total', 2);
            });
        })
    })

    it('Can delete datastore resource via API', () => {
        const token_data = Cypress.env('token_data');
        cy.request({
            method: 'GET',
            url: '/api/action/package_show?id=test-dataset-1',
            headers: {
                'Authorization': token_data.api_token
            }
        }).then((response) => {
            expect(response.body).to.have.property('success', true);
            const resource_id = response.body.result.resources[0].id;
            // delete resource with datastore_delete api
            var options = {
                'method': 'POST',
                'url': '/api/3/action/datastore_delete',
                'headers': {
                    'cache-control': 'no-cache',
                    'content-type': 'application/json',
                    'Authorization': token_data.api_token
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
