# sansJson
[![Tests](https://github.com/nickumia/sansjson/actions/workflows/commit.yml/badge.svg)](https://github.com/nickumia/sansjson/actions/workflows/commit.yml)
[![PyPI version](https://badge.fury.io/py/sansjson.svg)](https://badge.fury.io/py/sansjson)
[![codecov](https://codecov.io/gh/nickumia/sansJson/graph/badge.svg?token=102NN3LK3F)](https://codecov.io/gh/nickumia/sansJson)

Your friendly neighborhood JSON sorter helper!

This package is meant to rival the native `sort_keys` option of the `json`
package.  `sort_keys` only re-orders the keys according to the alphanumeric
priority.  This method breaks down when internal components (such as `lists`)
need to be re-ordered as well.  To ensure consistency across the entire JSON
object, as in the event of a `hash`, a recursive reordering of sortable
components may be necessary.  The following situations are covered:

Note:
- Homogenous: All elements in a specific component are the same data type.
(e.g. `{'a': [1,2,3], 'b', [2,3,4], 'c': [3,4,5]}`)
- Nonhomogenous: Each element in a specific component may be any of the
supported JSON types. (e.g. `{'a': [1, 'z', False], 0: [3,4,5]}`)
- The default priority for nonhomogenous types is:
  1. `null`
  1. `boolean`
  1. `number (int > float)`
  1. `string`
  1. `array`
  1. `object`

- Multi-level `dict` JSON (homogenous + nonhomogenous)
- `array` JSON (homogenous + nonhomogenous)
  - All types except python `object`

The following cases are not supported:
- python `objects` (i.e. classes)


## Installation

```bash
pip install sansjson
```

### How to use

```python
>>> import sansjson
>>> to_sort = {'a': 0, 'g': [3, 1, 3, 2], 'c': 1, 'f': 2}
>>> sansjson.sort_pyobject(to_sort)
{'a': 0, 'c': 1, 'f': 2, 'g': [1, 2, 3, 3]}
>>> a = '{"z": 1, "a": {"12": true, "ef": ["a", 1, false], "ap": 0}}'
>>> sansjson.sort_json(a)
'{"a": {"12": true, "ap": 0, "ef": [false, 1, "a"]}, "z": 1}'
```
