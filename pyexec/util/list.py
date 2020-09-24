from typing import List, TypeVar

T = TypeVar("T")


def all_equal(lst: List[T]) -> bool:
    if len(lst) == 0:
        return True

    first = lst[0]
    for e in lst:
        if not e == first:
            return False
    return True
