
from copy import deepcopy
import functools
import json
import logging

log = logging.getLogger(__name__)

NONHOMOGENOUS_ORDER = {
    type(None): 1, bool: 2, int: 3, float: 4, str: 5, list: 6,
    object: 7, dict: 8
}


class Hasher:
    '''
    Hash class to ensure exact match

    If the json string representation is the same, it is guaranteed that
    the sorting was successful.

    Note: As of Python 3.7+, the insertion order of dictionaries are preserved.
    (https://docs.python.org/3.7/library/stdtypes.html#typesmapping)
    '''
    def __init__(self):
        self._data = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        self._data = v

    def __hash__(self):
        return hash(json.dumps(self.data))

    def __eq__(self, other):
        if isinstance(other, Sorter):
            return hash(self) == hash(Sorter)
        return NotImplemented


class Sorter(Hasher):
    '''
    Sorter class to check sortability + perform sorting

    Supported types:
        - _dict_: sort key order
        - _list_: see 'nonhomogenous'
        - _str_: convert to _dict_
    '''

    def __init__(self):
        super(Sorter, self).__init__()

    def is_sortable(self, deck):
        if isinstance(deck, dict):
            self.data = deck
            return True
        if isinstance(deck, list):
            self.data = deck
            return True
        return False

    def is_json_sortable(self, deck):
        if isinstance(deck, str):
            try:
                self.data = json.loads(deck)
                return True
            except json.decoder.JSONDecodeError:
                return False
        return False

    def recursive_dict(self, context):
        sorted_dict = {}
        keys = nonhomogenous(context.keys())
        for k in keys:
            if self.is_sortable(context[k]):
                # BRANCH: recursively sort values
                sorted_dict[k] = self.sort(context[k])
            else:
                # LEAF: basic data types
                sorted_dict[k] = context[k]
        return sorted_dict

    def sort(self, context=None):
        sorted_dict = {}
        if context is None:
            context = self.data

        if isinstance(context, list):
            # LEAF/SPROUT: list of anything
            # LEAF component -> it's just a list
            # SPROUT component -> dicts need further attention
            return nonhomogenous([
                self.recursive_dict(element) if isinstance(element, dict)
                else element for element in context
            ])
        if isinstance(context, dict):
            # BRANCH: sort keys + values
            sorted_dict = self.recursive_dict(context)

        return sorted_dict


def _convert_to_json(data):
    return json.dumps(data)


def dict_sort_key(dicta, dictb):
    '''
    Custom dictionary comparison function

    Iterate through all key-value pairs.  The first key or value that is
    smaller decides the sorting order.
    e.g.1.  a = {'q': 8, 'w': 2}
            b = {'q': 2, 'w': 8}
        --> b is smaller because 2 < 8 for 'q' key.

    e.g.2.  a = {'q': 2, 'w': 3}
            b = {'q': 2, 'w': 0}
        --> b is smaller because 0 < 3 for 'w' key.

    e.g.3.  a = {'q': 0, 'w': 0}
            b = {'q': 0, 'w': 0}
        --> a is smaller because both are identical and a was passed first.

    -1 --> dicta is smaller
    +1 --> dictb is smaller
    0 --> dicta == dictb

    NOTE 1: JSON keys are guaranteed to be 'str'.  This function has that
    assumption embedded.
    NOTE 2: Dictionaries are assumed to be sorted before this function call.
    '''
    dicta_list = False
    dictb_list = False
    try:
        k_a = list(dicta.keys())[0]
    except IndexError:
        # No more keys
        k_a = None
    except AttributeError:
        # list to list compare
        dicta_list = sorted([dicta], key=functools.cmp_to_key(dict_sort_key))
    try:
        k_b = list(dictb.keys())[0]
    except IndexError:
        # No more keys
        k_b = None
    except AttributeError:
        # list to list compare
        dictb_list = sorted([dictb], key=functools.cmp_to_key(dict_sort_key))

    if dicta_list and dictb_list:
        # WORST NIGHTMARE: full sorting not possible
        # Find the smallest keys between both dicts
        return sorted(dicta_list[0] + dictb_list[0],
                      key=functools.cmp_to_key(dict_sort_key))

    # Dict with less keys is 'smaller'
    if k_a is None and k_b is None:
        return 0
    if k_a is None and k_b is not None:
        return -1
    if k_a is not None and k_b is None:
        return 1

    # First, compare keys
    if k_a == k_b:
        v1_type = type(dicta[k_a])
        v2_type = type(dictb[k_b])
        # Second, compare values
        if v1_type != v2_type:
            # Most likely scenario -> one value is a list and the other is not.
            # Use NONHOMOGENOUS_ORDER to determine sorting priority
            if NONHOMOGENOUS_ORDER[v1_type] > NONHOMOGENOUS_ORDER[v2_type]:
                return 1
            else:
                return -1
        else:
            if dicta[k_a] == dictb[k_b]:
                # key-value pairs are equal ...
                # Delete them and move to the next key-value
                dicta_copy = deepcopy(dicta)
                dictb_copy = deepcopy(dictb)
                del dicta_copy[k_a], dictb_copy[k_b]
                return dict_sort_key(dicta_copy, dictb_copy)
            else:
                # WORST NIGHTMARE: same as the last nightmare ;)
                if isinstance(dicta[k_a], list) and isinstance(dictb[k_b], list):  # NOQA E501
                    if isinstance(dicta[k_a][0], dict) and isinstance(dictb[k_b][0], dict):  # NOQA E501
                        smallest_key = dict_sort_key(dicta[k_a], dictb[k_b])
                        # Find the first unique key that is smaller.
                        # Otherwise, all keys are the same, default to
                        # first dict as smaller.
                        for dict_items in smallest_key:
                            for key, value in dict_items.items():
                                if key in dicta[k_a][0]:
                                    if dicta[k_a][0][key] == value:
                                        if key not in dictb[k_b][0]:
                                            return -1
                                elif key in dictb[k_b][0]:
                                    if dictb[k_b][0][key] == value:
                                        if key not in dicta[k_a][0]:
                                            return 1
                elif dicta[k_a] > dictb[k_b]:
                    return 1
                elif dicta[k_a] < dictb[k_b]:
                    return -1
                return 0
    else:
        if k_a > k_b:
            return 1
        else:
            return -1


def nonhomogenous(sans):
    '''
    Handle special nonhomogenous list sorting

    Use NONHOMOGENOUS_ORDER to handle priority of data types.
    '''
    try:
        # homogenous
        return sorted(sans)
    except TypeError:
        # nonhomogenous
        data_groups = {}
        for element in sans:
            data_type = type(element)
            if data_type in data_groups:
                data_groups[data_type].append(element)
            else:
                data_groups[data_type] = [element]

        final = []
        for dt in NONHOMOGENOUS_ORDER:
            if dt in data_groups.keys():
                if isinstance(None, dt):
                    final += data_groups[dt]
                elif dict == dt:
                    final += sorted(data_groups[dt],
                                    key=functools.cmp_to_key(dict_sort_key))
                else:
                    final += sorted(data_groups[dt])

        return final
