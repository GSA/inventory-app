
import pytest


@pytest.mark.parametrize(
    'a, b, t',
    [
        # Super Basic
        (
            '{"a": "1"}', '{"a": "1"}', "json"
        ),
        # Two-levels with list as leaf
        (
            '{"z": 1, "a": {"12": true, "ef": ["a", 1, false], "ap": 0}}',
            '{"a": {"12": true, "ap": 0, "ef": [false, 1, "a"]}, "z": 1}',
            "json"
        ),
    ]
)
def test_sorted(a, b, t, compare):
    assert compare
