def add(a, b):
    return a + b

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def greet(name):
    return "hello " + name

result = add(3, 4)
assert result == 7

assert factorial(5) == 120
assert factorial(0) == 1

assert greet("world") == "hello world"

def no_return():
    x = 1

assert no_return() == None

def multi_return(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"

assert multi_return(5) == "positive"
assert multi_return(-3) == "negative"
assert multi_return(0) == "zero"
