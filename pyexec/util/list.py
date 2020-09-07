from collections import OrderedDict
from typing import List, TypeVar

T = TypeVar("T")


def flatten(lists: List[List[T]]) -> List[T]:
    return [item for sublist in lists for item in sublist]


def remove_duplicates(lst: List[T]) -> List[T]:
    return list(OrderedDict.fromkeys(lst))


def all_equal(lst: List[T]) -> bool:
    if len(lst) == 0:
        return True

    first = lst[0]
    for e in lst:
        if not e == first:
            return False
    return True


def diff(lst1: List[T], lst2: List[T]) -> List[T]:
    return list(set(lst1).symmetric_difference(set(lst2)))
