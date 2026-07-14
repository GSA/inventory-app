import pytest
from pathlib import Path

from ckanext.datagov_inventory.dcat import dcat_converter


class TestDCATConverter:

    @pytest.fixture
    def sample_v1_1_catalog(self):
        return {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "describedBy": "https://project-open-data.cio.gov/v1.1/schema/catalog.json",
            "modified": "2024-01-15T10:30:00",
            "dataset": [
                {
                    "title": "Test Dataset",
                    "identifier": "test-001",
                    "description": "A test dataset",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {"fn": "Jane Doe", "hasEmail": "mailto:jane@example.gov"}
                }
            ]
        }

    @pytest.fixture
    def sample_v1_1_catalog_with_transforms(self):
        return {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "describedBy": "https://project-open-data.cio.gov/v1.1/schema/catalog.json",
            "dataset": [
                {
                    "title": "Transform Test",
                    "identifier": "test-002",
                    "description": "Dataset with fields that need transformation",
                    "modified": "R/P1Y",
                    "temporal": "2020-01-01/2025-12-31",
                    "spatial": "United States",
                    "language": ["en-US"],
                    "accessLevel": "public",
                    "rights": "Public domain",
                    "conformsTo": "https://www.iso.org/standard/53798.html",
                    "landingPage": "https://example.gov/test",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {"fn": "Jane Doe", "hasEmail": "mailto:jane@example.gov"}
                }
            ]
        }

    def test_load_schema_registry_v1_1(self):
        schema_dir = Path(__file__).parent.parent.parent / "dcat" / "v1.1_definitions"
        registry = dcat_converter.load_schema_registry(schema_dir)
        assert registry is not None

    def test_load_schema_registry_v3_0(self):
        schema_dir = Path(__file__).parent.parent.parent / "dcat" / "definitions"
        registry = dcat_converter.load_schema_registry(schema_dir)
        assert registry is not None

    def test_convert_dcat_catalog_updates_conforms_to(self, sample_v1_1_catalog):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert "conformsTo" in result
        assert result["conformsTo"]["@type"] == "Standard"
        assert result["conformsTo"]["title"] == "DCAT-US 3.0"
        assert "3.0.0" in result["conformsTo"]["identifier"]

    def test_convert_dcat_catalog_removes_context(self, sample_v1_1_catalog):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert "@context" not in result

    def test_convert_dcat_catalog_removes_described_by(self, sample_v1_1_catalog):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert "describedBy" not in result

    def test_convert_dcat_catalog_normalizes_catalog_modified(self, sample_v1_1_catalog):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert result["modified"].endswith("Z")

    def test_convert_dcat_catalog_preserves_datasets(self, sample_v1_1_catalog):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert "dataset" in result
        assert len(result["dataset"]) == 1

    def test_convert_dcat_catalog_applies_all_transforms(self, sample_v1_1_catalog_with_transforms):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog_with_transforms)
        dataset = result["dataset"][0]

        assert "modified" not in dataset
        assert dataset["accrualPeriodicity"] == "annually"

        assert isinstance(dataset["temporal"], list)
        assert dataset["temporal"][0]["@type"] == "PeriodOfTime"

        assert isinstance(dataset["spatial"], list)
        assert dataset["spatial"][0]["@type"] == "Location"

        assert dataset["language"] == ["en"]

        assert "accessRights" in dataset

        assert isinstance(dataset["rights"], list)

        assert isinstance(dataset["conformsTo"], list)
        assert dataset["conformsTo"][0]["@type"] == "Standard"

        assert isinstance(dataset["landingPage"], dict)
        assert dataset["landingPage"]["@type"] == "Document"

    def test_convert_dcat_catalog_handles_empty_dataset_list(self):
        catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": []
        }
        result = dcat_converter.convert_dcat_catalog(catalog)
        assert result["dataset"] == []

    def test_convert_dcat_catalog_handles_missing_dataset_field(self):
        catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema"
        }
        result = dcat_converter.convert_dcat_catalog(catalog)
        assert result.get("dataset", []) == []

    def test_convert_dcat_catalog_does_not_modify_original(self, sample_v1_1_catalog):
        original_conformsTo = sample_v1_1_catalog["conformsTo"]
        dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert sample_v1_1_catalog["conformsTo"] == original_conformsTo
        assert "@context" in sample_v1_1_catalog

    def test_format_path_with_empty_path(self):
        assert dcat_converter.format_path([]) == "(root)"

    def test_format_path_with_field_names(self):
        assert dcat_converter.format_path(["dataset", "title"]) == "dataset.title"

    def test_format_path_with_array_indices(self):
        assert dcat_converter.format_path(["dataset", 0, "title"]) == "dataset[0].title"

    def test_is_null_type_error_returns_true_for_null_type(self):
        class MockError:
            validator = "type"
            validator_value = "null"

        assert dcat_converter.is_null_type_error(MockError()) is True

    def test_is_null_type_error_returns_false_for_other_types(self):
        class MockError:
            validator = "type"
            validator_value = "string"

        assert dcat_converter.is_null_type_error(MockError()) is False

    def test_extract_schema_name_from_ref(self):
        schema = {"$ref": "/dcat-us/3.0.0/definitions/concept"}
        assert dcat_converter.extract_schema_name(schema) == "Concept"

    def test_extract_schema_name_from_title(self):
        schema = {"title": "Dataset"}
        assert dcat_converter.extract_schema_name(schema) == "Dataset"

    def test_extract_schema_name_returns_none_for_empty(self):
        assert dcat_converter.extract_schema_name({}) is None
