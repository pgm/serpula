# Numeric builtins: abs, bool, complex, divmod, float, int, max, min, pow, round, sum

assert abs(-7) == 7
assert abs(3.5) == 3.5

assert bool(0) == False
assert bool(1) == True
assert bool("") == False
assert bool("x") == True

assert complex(3, 4) == (3 + 4j)

assert divmod(17, 5) == (3, 2)
assert divmod(-17, 5) == (-4, 3)

assert float("3.14") == 3.14
assert float(7) == 7.0

assert int(3.9) == 3
assert int(-3.9) == -3
assert int("42") == 42
assert int("ff", 16) == 255

assert max(1, 2, 3) == 3
assert max([4, 2, 7, 1]) == 7

assert min(1, 2, 3) == 1
assert min([4, 2, 7, 1]) == 1

assert pow(2, 10) == 1024
assert pow(2, 3, 5) == 3

assert round(3.14159, 2) == 3.14
assert round(2.5) == 2
assert round(3.5) == 4

assert sum([1, 2, 3, 4, 5]) == 15
assert sum(range(1, 6)) == 15
assert sum([1, 2, 3], 10) == 16
