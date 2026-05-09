# Introspection builtins: callable, getattr, hasattr, hash, id, isinstance, issubclass, object, type

assert type(42) == int
assert type("hello") == str
assert type([]) == list
assert type({}) == dict
assert type(3.14) == float
assert type(True) == bool

assert isinstance(42, int) == True
assert isinstance(True, int) == True
assert isinstance("hi", str) == True
assert isinstance([], list) == True
assert isinstance(42, str) == False
assert isinstance(42, (int, str)) == True
assert isinstance(42, (str, float)) == False

assert issubclass(bool, int) == True
assert issubclass(int, object) == True
assert issubclass(str, int) == False

assert callable(print) == True
assert callable(len) == True
assert callable(42) == False
assert callable("hello") == False

def my_func():
    return 1

assert callable(my_func) == True

x = [1, 2, 3]
assert getattr(x, "__len__")() == 3
assert getattr(x, "count")(2) == 1

assert hasattr([], "append") == True
assert hasattr([], "nonexistent") == False
assert hasattr("hello", "upper") == True

assert hash(42) == hash(42)
assert hash("hello") == hash("hello")
assert hash((1, 2, 3)) == hash((1, 2, 3))

a = object()
b = object()
assert id(a) == id(a)
assert id(a) != id(b)
