describe('CKAN Extensions', () => {
    
    it('Uses CKAN 2.9', () => {
        cy.request('/api/action/status_show').should((response) => {
            expect(response.body).to.have.property('success', true);
            expect(response.body.result).to.have.property('ckan_version', '2.9.7');
        });
    })

    it('Has all necessary extensions installed', () => {
        cy.request('/api/action/status_show').should((response) => {
            expect(response.body).to.have.property('success', true);
            const installed_extensions = response.body.result.extensions;
            expect(installed_extensions).to.include('datastore');
            expect(installed_extensions).to.include('xloader');
            expect(installed_extensions).to.include('stats');
            expect(installed_extensions).to.include('recline_view');
            expect(installed_extensions).to.include('googleanalyticsbasic');
            expect(installed_extensions).to.include('s3filestore');
            expect(installed_extensions).to.include('envvars');
            expect(installed_extensions).to.include('datastore');
            expect(installed_extensions).to.include('datagov_inventory');
            expect(installed_extensions).to.include('dcat_usmetadata');
            expect(installed_extensions).to.include('usmetadata');
            expect(installed_extensions).to.include('datajson');
            // TODO: Re-integrate saml2auth when automated testing is created for it
            // expect(installed_extensions).to.include('saml2auth');
        });
    })
})
