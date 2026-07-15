import pytest

from ckanext.datagov_inventory.dcat import transforms


class TestDCATv3Transforms:

    @pytest.fixture
    def sample_v1_1_dataset(self):
        return {
            "title": "Test Dataset",
            "identifier": "test-001",
            "description": "A test dataset",
            "modified": "2024-01-15",
            "temporal": "2020-01-01/2025-12-31",
            "spatial": "United States",
            "language": ["en-US"],
            "accessLevel": "public",
            "license": "https://creativecommons.org/publicdomain/zero/1.0/",
            "rights": "This data is in the public domain.",
            "describedBy": "https://example.gov/schema.json",
            "describedByType": "application/schema+json",
            "conformsTo": "https://www.iso.org/standard/53798.html",
            "landingPage": "https://example.gov/test-dataset",
            "issued": "2020-01-01",
            "publisher": {
                "@type": "Organization",
                "name": "Test Agency"
            },
            "distribution": [
                {
                    "accessURL": "https://example.gov/data.csv",
                    "format": "CSV"
                }
            ]
        }

    @pytest.fixture
    def sample_v1_1_catalog(self):
        return {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "describedBy": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.json"
            ),
            "dataset": []
        }

    def test_transform_modified_date(self):
        dataset = {"modified": "2024-01-15"}
        result = transforms.transform_modified(dataset)
        assert result["modified"] == "2024-01-15"

    def test_transform_modified_duration(self):
        dataset = {"modified": "R/P1Y"}
        result = transforms.transform_modified(dataset)
        assert "modified" not in result
        assert result["accrualPeriodicity"] == "annually"

    def test_transform_temporal(self):
        dataset = {"temporal": "2020-01-01/2025-12-31"}
        result = transforms.transform_temporal(dataset)
        assert isinstance(result["temporal"], list)
        assert len(result["temporal"]) == 1
        assert result["temporal"][0]["@type"] == "PeriodOfTime"
        assert result["temporal"][0]["startDate"] == "2020-01-01"
        assert result["temporal"][0]["endDate"] == "2025-12-31"

    def test_transform_spatial_string(self):
        dataset = {"spatial": "United States"}
        result = transforms.transform_spatial(dataset)
        assert isinstance(result["spatial"], list)
        assert result["spatial"][0]["@type"] == "Location"
        assert result["spatial"][0]["prefLabel"] == "United States"

    def test_transform_spatial_bbox(self):
        dataset = {"spatial": "-125,24,-66,50"}
        result = transforms.transform_spatial(dataset)
        assert isinstance(result["spatial"], list)
        assert result["spatial"][0]["@type"] == "Location"
        assert "bbox" in result["spatial"][0]
        assert result["spatial"][0]["bbox"].startswith("POLYGON")

    def test_transform_language(self):
        dataset = {"language": ["en-US", "es-MX"]}
        result = transforms.transform_language(dataset)
        assert result["language"] == ["en", "es"]

    def test_transform_access_rights(self):
        dataset = {"accessLevel": "public"}
        result = transforms.transform_access_rights(dataset)
        assert result["accessRights"] == "public"

        dataset = {"accessLevel": "restricted public"}
        result = transforms.transform_access_rights(dataset)
        assert "Contact the publisher" in result["accessRights"]

    def test_propagate_license(self):
        dataset = {
            "license": (
                "https://creativecommons.org/publicdomain/zero/1.0/"
            ),
            "distribution": [
                {"accessURL": "https://example.gov/data.csv"}
            ]
        }
        result = transforms.propagate_license(dataset)
        assert result["distribution"][0]["license"] == (
            "https://creativecommons.org/publicdomain/zero/1.0/"
        )

    def test_transform_rights(self):
        dataset = {"rights": "This data is in the public domain."}
        result = transforms.transform_rights(dataset)
        assert isinstance(result["rights"], list)
        assert result["rights"][0] == "This data is in the public domain."

    def test_transform_described_by(self):
        dataset = {
            "describedBy": "https://example.gov/schema.json",
            "describedByType": "application/schema+json"
        }
        result = transforms.transform_described_by(dataset)
        assert isinstance(result["describedBy"], dict)
        url = result["describedBy"]["accessURL"]
        assert url == "https://example.gov/schema.json"
        media = result["describedBy"]["mediaType"]
        assert media == "application/schema+json"
        assert "describedByType" not in result

    def test_transform_conforms_to(self):
        dataset = {
            "conformsTo": "https://www.iso.org/standard/53798.html"
        }
        result = transforms.transform_conforms_to(dataset)
        assert isinstance(result["conformsTo"], list)
        assert result["conformsTo"][0]["@type"] == "Standard"
        ident = result["conformsTo"][0]["identifier"]
        assert ident == "https://www.iso.org/standard/53798.html"

    def test_transform_landing_page(self):
        dataset = {
            "title": "Test Dataset",
            "landingPage": "https://example.gov/test-dataset"
        }
        result = transforms.transform_landing_page(dataset)
        assert isinstance(result["landingPage"], dict)
        assert result["landingPage"]["@type"] == "Document"
        url = result["landingPage"]["accessURL"]
        assert url == "https://example.gov/test-dataset"
        assert result["landingPage"]["title"] == "Test Dataset"

    def test_transform_issued(self):
        dataset = {"issued": "2020-01-01T00:00:00"}
        result = transforms.transform_issued(dataset)
        assert result["issued"] == "2020-01-01"

        dataset = {"issued": "2020-01-01T14:30:00"}
        result = transforms.transform_issued(dataset)
        assert result["issued"].endswith("Z")

    def test_transform_sub_organization_of(self):
        dataset = {
            "publisher": {
                "@type": "Organization",
                "name": "Sub-Agency",
                "subOrganizationOf": {
                    "@type": "Organization",
                    "name": "Parent Agency"
                }
            }
        }
        result = transforms.transform_sub_organization_of(dataset)
        sub_org = result["publisher"]["subOrganizationOf"]
        assert isinstance(sub_org, list)
        assert sub_org[0]["name"] == "Parent Agency"
