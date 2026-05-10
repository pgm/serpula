# *args, **kwargs — variadic positional and keyword parameters

def add(*args):
    total = 0
    for x in args:
        total += x
    return total

assert add() == 0
assert add(1) == 1
assert add(1, 2, 3) == 6

def tag(name, *args, **kwargs):
    attrs = ""
    for k in kwargs:
        attrs += " " + k + "=" + kwargs[k]
    content = ""
    for a in args:
        content += a
    return "<" + name + attrs + ">" + content + "</" + name + ">"

assert tag("b", "hello") == "<b>hello</b>"
assert tag("a", "click", href="/home") == '<a href=/home>click</a>'

# ** unpacking at call sites
def greet(name, greeting):
    return greeting + ", " + name + "!"

opts = {"name": "Alice", "greeting": "Hello"}
assert greet(**opts) == "Hello, Alice!"

# * unpacking at call sites
def three(a, b, c):
    return a + b + c

nums = [1, 2, 3]
assert three(*nums) == 6

# mixed unpacking
extra = [3]
assert three(1, 2, *extra) == 6

def first_rest(first, *rest):
    return first

assert first_rest(10, 20, 30) == 10

def only_kwargs(**kwargs):
    return kwargs

result = only_kwargs(x=1, y=2)
assert result == {"x": 1, "y": 2}

base = {"x": 1}
more = {"y": 2}
merged = only_kwargs(**base, **more)
assert merged == {"x": 1, "y": 2}

print("star_args ok")
