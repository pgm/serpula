# Keyword arguments and default parameter values

def greet(name, greeting="Hello"):
    return greeting + ", " + name + "!"

assert greet("Alice") == "Hello, Alice!"
assert greet("Bob", "Hi") == "Hi, Bob!"
assert greet("Carol", greeting="Hey") == "Hey, Carol!"
assert greet(name="Dave", greeting="Yo") == "Yo, Dave!"

# Multiple defaults
def describe(item, color="red", size="medium"):
    return color + " " + size + " " + item

assert describe("ball") == "red medium ball"
assert describe("ball", color="blue") == "blue medium ball"
assert describe("ball", size="large") == "red large ball"
assert describe("ball", color="green", size="small") == "green small ball"

# Keyword args to built-ins
def neg(x):
    return -x

assert sorted([3, 1, 2], key=neg) == [3, 2, 1]
assert list(map(neg, [1, 2, 3])) == [-1, -2, -3]

# Method with default arg
class Greeter:
    def __init__(self, default_greeting="Hello"):
        self.default_greeting = default_greeting

    def greet(self, name, greeting=None):
        if greeting is None:
            greeting = self.default_greeting
        return greeting + ", " + name + "!"

g = Greeter()
assert g.greet("Alice") == "Hello, Alice!"
assert g.greet("Bob", greeting="Hi") == "Hi, Bob!"

g2 = Greeter(default_greeting="Hey")
assert g2.greet("Carol") == "Hey, Carol!"

print("kwargs ok")
