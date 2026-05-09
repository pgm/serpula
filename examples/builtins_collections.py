# Collection builtins: dict, enumerate, frozenset, len, list, range, reversed, set, slice, sorted, tuple, zip

assert list(range(5)) == [0, 1, 2, 3, 4]
assert list(range(2, 8)) == [2, 3, 4, 5, 6, 7]
assert list(range(0, 10, 3)) == [0, 3, 6, 9]
assert list(range(5, 0, -1)) == [5, 4, 3, 2, 1]

assert tuple([1, 2, 3]) == (1, 2, 3)
assert tuple("abc") == ("a", "b", "c")

assert list({3, 1, 2}) == sorted([1, 2, 3])
assert set([1, 2, 2, 3, 3, 3]) == {1, 2, 3}

assert frozenset([1, 2, 2, 3]) == frozenset({1, 2, 3})

assert dict([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}

assert len([1, 2, 3]) == 3
assert len("hello") == 5
assert len({}) == 0
assert len((1, 2)) == 2

assert sorted([3, 1, 4, 1, 5, 9, 2]) == [1, 1, 2, 3, 4, 5, 9]
assert sorted("dcba") == ["a", "b", "c", "d"]

assert list(reversed([1, 2, 3])) == [3, 2, 1]
assert list(reversed("abc")) == ["c", "b", "a"]

assert list(enumerate(["a", "b", "c"])) == [(0, "a"), (1, "b"), (2, "c")]
assert list(enumerate(["a", "b"], 5)) == [(5, "a"), (6, "b")]

assert list(zip([1, 2, 3], ["a", "b", "c"])) == [(1, "a"), (2, "b"), (3, "c")]
assert list(zip([1, 2], ["a", "b", "c"])) == [(1, "a"), (2, "b")]

x = [0, 1, 2, 3, 4]
assert x[slice(1, 4)] == [1, 2, 3]
assert x[slice(None, None, 2)] == [0, 2, 4]
