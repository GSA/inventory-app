
import pytest
from sansjson.utils import Hasher

o = Hasher()


# TODO: fix objects
@pytest.mark.parametrize(
    'a, b, t',
    [
        # Homogenous
        (
            [3, 5, 4, 2],
            [2, 3, 4, 5], 'pyobject'
        ),
        # Non-Homogenous
        (
            [None, 'a', 2, None],
            [None, None, 2, 'a'], 'pyobject'
        ),
        # Non-Homogenous Array 2
        (
            ['z', 1, 'a', 2, 'y', 3, 'c', 4],
            [1, 2, 3, 4, 'a', 'c', 'y', 'z'], 'pyobject'
        ),
        # Non-Homogenous 3
        (
            [None, 'z', 2, None, True, False, 1, 'a'],
            [None, None, False, True, 1, 2, 'a', 'z'], 'pyobject'
        ),
        # Array of 'objects'
        (
            [{'z': 1, 'a': 2}, {'y': 3, 'c': 4}],
            [{'a': 2, 'z': 1}, {'c': 4, 'y': 3}], 'pyobject'
        ),
        # Array of 'objects' + other stuff
        (
            [{'z': 10, 'a': 2},
             {'y': 3, 'c': 4}, 'a', 1, {'z': 1, 'a': 2}, True],
            [True, 1, 'a',
             {'a': 2, 'z': 1}, {'a': 2, 'z': 10}, {'c': 4, 'y': 3}], 'pyobject'
        ),
        # Array of 'objects' + other stuff 2
        (
            [{'z': 10, 'a': 2, 'y': 3}, 'a', 1,
             {'a': [{'y': 3}, {'y': 0}, {'r': 0}]},
             {'a': [{'x': 9}, {'s': 8}]}, True],
            [True, 1, 'a', {'a': 2, 'y': 3, 'z': 10},
             {'a': [{'r': 0}, {'y': 0}, {'y': 3}]},
             {'a': [{'s': 8}, {'x': 9}]}], 'pyobject'
        ),
        # Array of dicts -- first dict longer
        (
            [{'a': 1, 'c': 3, 'b': 2}, {'b': 2, 'a': 1}],
            [{'a': 1, 'b': 2}, {'a': 1, 'b': 2, 'c': 3}], 'pyobject'
        ),
        # Array of dicts -- second dict longer
        (
            [{'b': 2, 'a': 1}, {'a': 1, 'c': 3, 'b': 2}],
            [{'a': 1, 'b': 2}, {'a': 1, 'b': 2, 'c': 3}], 'pyobject'
        ),
        # Array of dicts -- dicts are the same size
        (
            [{'b': 2, 'a': 1}, {'a': 1, 'b': 2}],
            [{'a': 1, 'b': 2}, {'a': 1, 'b': 2}], 'pyobject'
        ),
        # Array of dicts -- nonhomogenous values
        # TODO: doesn't work
        # (
        #     [{'a': [1, {1: 3}, False]}, {'a': [1, {1: 1}, False]}],
        #     [{'a': [False, 1, {1: 1}]}, {'a': [False, 1, {1: 3}]}]
        # ),
        # Array of dicts -- value variant 2
        (
            [{'a': [{1: 3}, {1: 1}]}, {'a': [{1: 5}, {1: 1}]}],
            [{'a': [{1: 1}, {1: 3}]}, {'a': [{1: 1}, {1: 5}]}], 'pyobject'
        ),
        # Array of dicts -- value variant 3
        (
            [{'a': [{2: 3}, {1: 1}]}, {'a': [{4: 5}, {1: 1}]}],
            [{'a': [{1: 1}, {2: 3}]}, {'a': [{1: 1}, {4: 5}]}], 'pyobject'
        ),
        # Array of dicts -- value variant 4 (list + non-list)
        (
            [{'a': [{1: 3}, {1: 1}]}, {'a': 1}],
            [{'a': 1}, {'a': [{1: 1}, {1: 3}]}], 'pyobject'
        ),
    ]
)
def test_sortable_homogenous(a, b, t, compare):
    assert compare
