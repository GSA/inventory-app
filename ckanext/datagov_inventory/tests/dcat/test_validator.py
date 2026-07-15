import pytest

from ckanext.datagov_inventory.dcat import validator


class TestV1ValidationTracking:

    @pytest.fixture
    def invalid_v1_1_catalog(self):
        return {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Missing Required Fields",
                    "identifier": "invalid-001"
                },
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "A valid dataset",
                    "modified": "2024-01-15",
                    "keyword": ["valid", "test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    def test_validate_v1_1_catalog_returns_validation_errors(
        self, invalid_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(invalid_v1_1_catalog)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_v1_1_catalog_includes_dataset_context(
        self, invalid_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(invalid_v1_1_catalog)
        invalid_dataset_errors = [
            e for e in errors if e.get("identifier") == "invalid-001"
        ]
        assert len(invalid_dataset_errors) > 0
        assert "identifier" in invalid_dataset_errors[0]
        assert "title" in invalid_dataset_errors[0]
        assert "errors" in invalid_dataset_errors[0]

    def test_validate_v1_1_catalog_returns_empty_for_valid(
        self, sample_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(sample_v1_1_catalog)
        assert errors == []

    def test_validate_v1_1_catalog_counts_valid_and_invalid(
        self, invalid_v1_1_catalog
    ):
        valid, invalid, errors = validator.validate_v1_1_catalog_with_counts(
            invalid_v1_1_catalog
        )
        assert valid == 1
        assert invalid == 1
        assert len(errors) == 1

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
                    "keyword": ["test", "dataset"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }


class TestV3ValidationTracking:

    @pytest.fixture
    def invalid_v3_0_catalog(self):
        return {
            "conformsTo": {
                "@type": "Standard",
                "title": "DCAT-US 3.0",
                "identifier": "https://resources.data.gov/dcat-us/3.0.0"
            },
            "dataset": [
                {
                    "title": "Missing Required Fields",
                    "identifier": "invalid-v3-001"
                },
                {
                    "title": "Valid V3 Dataset",
                    "identifier": "valid-v3-001",
                    "description": "A valid v3.0 dataset",
                    "modified": "2024-01-15T10:30:00Z",
                    "keyword": ["valid", "test"],
                    "accessLevel": "public",
                    "accessRights": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    def test_validate_v3_0_catalog_returns_validation_errors(
        self, invalid_v3_0_catalog
    ):
        errors = validator.validate_v3_0_catalog(invalid_v3_0_catalog)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_v3_0_catalog_includes_dataset_context(
        self, invalid_v3_0_catalog
    ):
        errors = validator.validate_v3_0_catalog(invalid_v3_0_catalog)
        invalid_dataset_errors = [
            e for e in errors if e.get("identifier") == "invalid-v3-001"
        ]
        assert len(invalid_dataset_errors) > 0
        assert "identifier" in invalid_dataset_errors[0]
        assert "title" in invalid_dataset_errors[0]
        assert "errors" in invalid_dataset_errors[0]

    def test_validate_v3_0_catalog_returns_empty_for_valid(self):
        valid_catalog = {
            "conformsTo": {
                "@type": "Standard",
                "title": "DCAT-US 3.0",
                "identifier": "https://resources.data.gov/dcat-us/3.0.0"
            },
            "dataset": [
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "A valid dataset",
                    "modified": "2024-01-15T10:30:00Z",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "accessRights": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        errors = validator.validate_v3_0_catalog(valid_catalog)
        assert errors == []

    def test_validate_v3_0_catalog_counts_valid_and_invalid(
        self, invalid_v3_0_catalog
    ):
        valid, invalid, errors = validator.validate_v3_0_catalog_with_counts(
            invalid_v3_0_catalog
        )
        assert valid == 1
        assert invalid == 1
        assert len(errors) == 1
