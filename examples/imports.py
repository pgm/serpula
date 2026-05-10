# import statements — compiled to __import__() calls like CPython

import os
assert os.sep == os.sep  # just check it bound

import os.path
assert os.path.join("a", "b") == os.path.join("a", "b")

import os.path as osp
assert osp.join("x", "y") == os.path.join("x", "y")

from os.path import join
assert join("a", "b") == os.path.join("a", "b")

from os.path import join as j, exists
assert j("a", "b") == os.path.join("a", "b")
assert exists("/") == True

import math
assert math.floor(3.7) == 3
assert math.ceil(3.2) == 4

from math import sqrt, pi
assert sqrt(4) == 2.0
assert pi > 3.14

print("imports ok")
