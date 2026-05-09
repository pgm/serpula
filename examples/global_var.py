counter = 0

def increment():
    global counter
    counter = counter + 1

def reset():
    global counter
    counter = 0

increment()
increment()
increment()
assert counter == 3

reset()
assert counter == 0

total = 0

def add_to_total(x):
    global total
    total = total + x

add_to_total(10)
add_to_total(20)
assert total == 30
