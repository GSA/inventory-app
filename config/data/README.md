# Adding an Organization to inventory.data.gov

1. Log in to inventory, click `Organizations`, then `Add Organization` button.
2. Fill out the `Name`, `Description`, and `Image` fields
    1. If the org name is long, consider manually changing the URL to a shorter, logical string. Example: `Agricultural Research Service, Department of Agriculture` becomes inventory.data.gov/organization/ars-usda-gov
3. Save the org
4. If the new org is a sub-org of a larger agency/organization (meaning when the larger/main org exports a data.json file, the application will pull the data.json from the sub-org inventory and incorporate it into the final output), navigate to the **main** org page and click `Admin` 
5. On main org `admin` page, either add a key of `sub-agencies` in the custom fields and add a `value` or edit the `value` field if the key already exists.
    1. The value formatting should follow `org-url-id` and be comma-separated, such as `olm-doe,fossil-energy,cfo-energy-gov`

# Adding Publishers to an Organization

Without manually adding a publisher to an org, no publisher will appear in the dropdown when an inventory user creates a new dataset record.

1. Open https://github.com/GSA/inventory-app/blob/main/config/data/inventory_publishers.csv and click `Edit this file`
2. For a brand new org, add a row in the correct alphabetical spot
    1. The first column should be the `org-url-id`, followed by the `Full Text Name of Main Org`, followed by (optionally) `Name of Sub-org` OR `Additional Publishers Desired in the Org`, comma-separated, and ending with `,,,,`
    2. Examples: `nrel-gov,Department of Energy,National Renewable Energy Laboratory,,,,` OR `state-gov,Department of State,,,,,` OR `department-of-energy,Department of Energy,Office of Nuclear Energy,Idaho National Laboratory,,,`
3. For an existing org, add a row that adds the new Publisher in the correct column of the hierarchy
4. Create a Pull Request 

Of note, any org (even a sub-org) in the inventory will need its own row with a publisher. A sub-org of DOE cannot just add a line in to the `department-of-energy` block, it must have its own row with its own org ID in the first column.

# Adding Users to Inventory

**Important Note**: Despite the inventory.data.gov UI providing buttons for an admin to `Add a User`, due to the integration with login.gov, adding users via the UI is no longer supported. Adding a user via the UI will only confuse SAML and cause issues.

### Non-developer instructions:

1. Fill out an issue to add a user at https://github.com/GSA/datagov-account-management/issues using the `New User Account` template
2. Make sure the dropdown lists `inventory.data.gov` as the application
3. Choose `Editor` permissions for any non-datagov team member

### Developer instructions:

1. TBD





