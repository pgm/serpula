# String & bytes builtins: ascii, bin, bytearray, bytes, chr, format, hex, oct, ord, repr, str

assert str(42) == "42"
assert str(3.14) == "3.14"
assert str(True) == "True"

assert chr(65) == "A"
assert chr(9731) == "☃"

assert ord("A") == 65
assert ord("☃") == 9731

assert bin(0) == "0b0"
assert bin(10) == "0b1010"
assert bin(-3) == "-0b11"

assert hex(0) == "0x0"
assert hex(255) == "0xff"
assert hex(-1) == "-0x1"

assert oct(0) == "0o0"
assert oct(8) == "0o10"
assert oct(-8) == "-0o10"

assert repr("hello") == "'hello'"
assert repr([1, 2, 3]) == "[1, 2, 3]"
assert repr(None) == "None"

assert ascii("café") == "'caf\\xe9'"
assert ascii("hello") == "'hello'"

assert format(3.14159, ".2f") == "3.14"
assert format(255, "x") == "ff"
assert format(42, "08b") == "00101010"

assert bytes([72, 101, 108, 108, 111]) == b"Hello"
assert bytes(3) == b"\x00\x00\x00"

assert bytearray([72, 101, 108, 108, 111]) == bytearray(b"Hello")
assert bytearray(3) == bytearray(b"\x00\x00\x00")
