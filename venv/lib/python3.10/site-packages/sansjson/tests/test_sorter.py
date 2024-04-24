
import pytest
from sansjson.utils import Hasher


@pytest.mark.parametrize(
    'a, p, j',
    [
        # dict
        ({'a': 1, 'b': 2, 'c': 3}, True, False),
        # JSON str
        ('{"a": 1, "b": 2, "c": 3}', False, True),
        # list
        ([1, 3, 2], True, False),
        # JSON str (bad)
        ('{"a": 1, "b": 2, "c: 3}', False, False),
        # int
        (1, False, False),
        # none
        (None, False, False),
        # object
        (Hasher(), False, False)
    ]
)
def test_sortable(a, p, j, sortable_test):
    assert sortable_test
