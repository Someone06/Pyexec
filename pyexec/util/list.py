from collections import OrderedDict
from typing import List, TypeVar

T = TypeVar("T")


def flatten(lists: List[List[T]]) -> List[T]:
    return [item for sublist in lists for item in sublist]


def remove_duplicates(lst: List[T]) -> List[T]:
    return list(OrderedDict.fromkeys(lst))
