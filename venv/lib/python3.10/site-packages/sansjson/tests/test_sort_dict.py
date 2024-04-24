
import pytest


@pytest.mark.parametrize(
    'a, b, t',
    [
        # One-level
        (
            {'z': 1, 'a': 2, 'y': 3, 'c': 4},
            {'a': 2, 'c': 4, 'y': 3, 'z': 1}, 'pyobject'
        ),
        # Two-levels
        (
            {'z': 1,
             'a': {
                 '12': True,
                 'ef': False,
                 'ap': 0},
             'y': 3,
             'c': {
                 'yh': 'abc',
                 'ue': 'def',
                 '0': 'werg'}},
            {'a': {
                '12': True,
                'ap': 0,
                'ef': False},
             'c': {
                 '0': 'werg',
                 'ue': 'def',
                 'yh': 'abc'},
             'y': 3,
             'z': 1}, 'pyobject'
        ),
        # Three-levels
        (
            {'z': 1,
             'a': {
                 '12': True,
                 'ef': {
                     'def': 23,
                     'erf': 45,
                     'cop': 67},
                 'ap': 0},
             'y': 3,
             'c': {
                 'yh': 'abc',
                 'ue': 'def',
                 '0': {
                     'jun': False,
                     'jul': True,
                     'aug': 1}}},
            {'a': {
                '12': True,
                'ap': 0,
                'ef': {
                    'cop': 67,
                    'def': 23,
                    'erf': 45}},
             'c': {
                 '0': {
                     'aug': 1,
                     'jul': True,
                     'jun': False},
                 'ue': 'def',
                 'yh': 'abc'},
             'y': 3,
             'z': 1}, 'pyobject'
        ),
        # Two-levels with list as leaf
        (
            {'z': 1,
             'a': {
                 '12': True,
                 'ef': ['a', 1, False],
                 'ap': 0}},
            {'a': {
                '12': True,
                'ap': 0,
                'ef': [False, 1, 'a']},
             'z': 1}, 'pyobject'
        ),
    ]
)
def test_sorted(a, b, t, compare):
    assert compare
