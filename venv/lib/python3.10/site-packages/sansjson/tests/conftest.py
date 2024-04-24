
import pytest
import sansjson
from sansjson.utils import Hasher, Sorter


@pytest.fixture(scope='function')
def compare(a, b, t):
    if t == 'json':
        c = sansjson.sort_json(a)
    else:
        c = sansjson.sort_pyobject(a)

    reference = Hasher()
    reference.data = b

    good = Hasher()
    good.data = c

    assert hash(good) == hash(reference)

    return True


@pytest.fixture(scope='function')
def sortable_test(a, p, j):
    m = Sorter()

    assert m.is_sortable(a) is p
    assert m.is_json_sortable(a) is j
    return True
