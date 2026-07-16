import pytest
from pathlib import Path

from ckanext.datagov_inventory.dcat import dcat_converter, validator


class TestDCATConverter:

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
            "modified": "2024-01-15T10:30:00",
            "dataset": [
                {
                    "title": "Test Dataset",
                    "identifier": "test-001",
                    "description": "A test dataset",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_v1_1_catalog_with_transforms(self):
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
            "dataset": [
                {
                    "title": "Transform Test",
                    "identifier": "test-002",
                    "description": (
                        "Dataset with fields that need transformation"
                    ),
                    "modified": "R/P1Y",
                    "temporal": "2020-01-01/2025-12-31",
                    "spatial": "United States",
                    "language": ["en-US"],
                    "accessLevel": "public",
                    "rights": "Public domain",
                    "conformsTo": "https://www.iso.org/standard/53798.html",
                    "landingPage": "https://example.gov/test",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    def test_load_schema_registry_v1_1(self):
        schema_dir = (
            Path(__file__).parent.parent.parent
            / "dcat" / "v1.1_definitions"
        )
        registry = validator.load_schema_registry(schema_dir)
        assert registry is not None

    def test_load_schema_registry_v3_0(self):
        schema_dir = (
            Path(__file__).parent.parent.parent / "dcat" / "definitions"
        )
        registry = validator.load_schema_registry(schema_dir)
        assert registry is not None

    def test_convert_dcat_catalog_updates_conforms_to(
        self, sample_v1_1_catalog
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert "conformsTo" in result
        assert result["conformsTo"]["@type"] == "Standard"
        assert result["conformsTo"]["title"] == "DCAT-US 3.0"
        assert "3.0.0" in result["conformsTo"]["identifier"]

    def test_convert_dcat_catalog_removes_context(
        self, sample_v1_1_catalog
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert "@context" not in result

    def test_convert_dcat_catalog_removes_described_by(
        self, sample_v1_1_catalog
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert "describedBy" not in result

    def test_convert_dcat_catalog_normalizes_catalog_modified(
        self, sample_v1_1_catalog
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert result["modified"].endswith("Z")

    def test_convert_dcat_catalog_preserves_datasets(
        self, sample_v1_1_catalog
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert "dataset" in result
        assert len(result["dataset"]) == 1

    def test_convert_dcat_catalog_applies_all_transforms(
        self, sample_v1_1_catalog_with_transforms
    ):
        result, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog_with_transforms
        )
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
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": []
        }
        result, errors = dcat_converter.convert_dcat_catalog(catalog)
        assert result["dataset"] == []

    def test_convert_dcat_catalog_handles_missing_dataset_field(self):
        catalog = {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema"
        }
        result, errors = dcat_converter.convert_dcat_catalog(catalog)
        assert result.get("dataset", []) == []

    def test_convert_dcat_catalog_does_not_modify_original(
        self, sample_v1_1_catalog
    ):
        original_conformsTo = sample_v1_1_catalog["conformsTo"]
        catalog, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert sample_v1_1_catalog["conformsTo"] == original_conformsTo
        assert "@context" in sample_v1_1_catalog

    def test_format_path_with_empty_path(self):
        assert validator.format_path([]) == "(root)"

    def test_format_path_with_field_names(self):
        result = validator.format_path(["dataset", "title"])
        assert result == "dataset.title"

    def test_format_path_with_array_indices(self):
        result = validator.format_path(["dataset", 0, "title"])
        assert result == "dataset[0].title"

    def test_is_null_type_error_returns_true_for_null_type(self):
        class MockError:
            validator = "type"
            validator_value = "null"

        assert validator.is_null_type_error(MockError()) is True

    def test_is_null_type_error_returns_false_for_other_types(self):
        class MockError:
            validator = "type"
            validator_value = "string"

        assert validator.is_null_type_error(MockError()) is False

    def test_extract_schema_name_from_ref(self):
        schema = {"$ref": "/dcat-us/3.0.0/definitions/concept"}
        assert validator.extract_schema_name(schema) == "Concept"

    def test_extract_schema_name_from_title(self):
        schema = {"title": "Dataset"}
        assert validator.extract_schema_name(schema) == "Dataset"

    def test_extract_schema_name_returns_none_for_empty(self):
        assert validator.extract_schema_name({}) is None

    def test_convert_dcat_catalog_returns_tuple_with_catalog_and_errors(
        self, sample_v1_1_catalog
    ):
        result = dcat_converter.convert_dcat_catalog(sample_v1_1_catalog)
        assert isinstance(result, tuple)
        assert len(result) == 2
        catalog, errors = result
        assert isinstance(catalog, dict)
        assert isinstance(errors, list)

    def test_convert_dcat_catalog_returns_empty_errors_for_valid_datasets(
        self, sample_v1_1_catalog
    ):
        catalog, errors = dcat_converter.convert_dcat_catalog(
            sample_v1_1_catalog
        )
        assert errors == []
        assert len(catalog["dataset"]) == 1

    def test_convert_dcat_catalog_captures_transformation_errors(self):
        import unittest.mock as mock
        from ckanext.datagov_inventory.dcat import transforms

        catalog_with_datasets = {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "This should work",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                },
                {
                    "title": "Bad Dataset",
                    "identifier": "bad-001",
                    "description": "This will fail transformation",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        original_transform = transforms.transform_temporal

        def mock_transform_temporal(dataset):
            if dataset.get("identifier") == "bad-001":
                raise ValueError("Simulated transformation error")
            return original_transform(dataset)

        with mock.patch.object(
            transforms, 'transform_temporal',
            side_effect=mock_transform_temporal
        ):
            catalog, errors = dcat_converter.convert_dcat_catalog(
                catalog_with_datasets
            )

        assert len(errors) == 1
        assert errors[0]["identifier"] == "bad-001"
        assert len(catalog["dataset"]) == 1
        assert catalog["dataset"][0]["identifier"] == "valid-001"

    def test_convert_dcat_catalog_error_includes_dataset_metadata(self):
        catalog_with_bad_dataset = {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Error Dataset",
                    "identifier": "error-001",
                    "description": "This will error",
                    "modified": "2024-01-15",
                    "temporal": None,
                    "accessLevel": "public",
                    "publisher": {"name": "Error Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }
        catalog, errors = dcat_converter.convert_dcat_catalog(
            catalog_with_bad_dataset
        )
        if len(errors) > 0:
            error = errors[0]
            assert "identifier" in error
            assert error["identifier"] == "error-001"
            assert "title" in error
            assert error["title"] == "Error Dataset"
            assert "error" in error

    def test_convert_dcat_catalog_continues_processing_after_error(self):
        import unittest.mock as mock
        from ckanext.datagov_inventory.dcat import transforms

        catalog_with_mixed_datasets = {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "First Valid",
                    "identifier": "valid-001",
                    "description": "Should succeed",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                },
                {
                    "title": "Error Dataset",
                    "identifier": "error-001",
                    "description": "Should fail",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                },
                {
                    "title": "Second Valid",
                    "identifier": "valid-002",
                    "description": "Should also succeed",
                    "modified": "2024-01-15",
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        original_transform = transforms.transform_spatial

        def mock_transform_spatial(dataset):
            if dataset.get("identifier") == "error-001":
                raise RuntimeError("Simulated spatial transform error")
            return original_transform(dataset)

        with mock.patch.object(
            transforms, 'transform_spatial', side_effect=mock_transform_spatial
        ):
            catalog, errors = dcat_converter.convert_dcat_catalog(
                catalog_with_mixed_datasets
            )

        assert len(catalog["dataset"]) == 2
        assert catalog["dataset"][0]["identifier"] == "valid-001"
        assert catalog["dataset"][1]["identifier"] == "valid-002"
        assert len(errors) == 1
        assert errors[0]["identifier"] == "error-001"

