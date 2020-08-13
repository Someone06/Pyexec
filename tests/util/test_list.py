from pyexec.util.list import flatten, remove_duplicates


def test_flatten_empty():
    assert(flatten(list(list())) == list())


def test_flatten_simple():
    assert(flatten([[1]]) == [1])


def test_flatten_complex():
    assert(flatten([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5])


def test_remove_duplicates_empty():
    assert(remove_duplicates([]) == [])


def test_remove_duplicates_simple():
    assert(remove_duplicates([1, 2, 2, 3, 3, 3, 4, 4, 4, 4]) == [1, 2, 3, 4])


def test_remove_duplicates_complex():
    assert(remove_duplicates([1, 2, 1, 2, 3, 4, 3, 4, 2, 1, 4]) == [1, 2, 3, 4])
