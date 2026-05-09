# Iteration & functional builtins: all, any, filter, iter, map, next

assert all([True, True, True]) == True
assert all([True, False, True]) == False
assert all([]) == True

assert any([False, False, True]) == True
assert any([False, False, False]) == False
assert any([]) == False

it = iter([10, 20, 30])
assert next(it) == 10
assert next(it) == 20
assert next(it) == 30

def is_even(x):
    return x % 2 == 0

def square(x):
    return x * x

def negate(x):
    return -x

assert list(filter(is_even, [1, 2, 3, 4, 5, 6])) == [2, 4, 6]
assert list(filter(is_even, [])) == []

assert list(map(square, [1, 2, 3, 4])) == [1, 4, 9, 16]
assert list(map(negate, [1, -2, 3])) == [-1, 2, -3]

# map with two iterables
def add(a, b):
    return a + b

assert list(map(add, [1, 2, 3], [10, 20, 30])) == [11, 22, 33]
