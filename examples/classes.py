# Classes: basic class definitions, inheritance, methods, class variables

class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return self.name + " says " + self.sound

class Dog(Animal):
    def fetch(self):
        return self.name + " fetches the ball!"

a = Animal("Cat", "meow")
assert a.speak() == "Cat says meow"

d = Dog("Rex", "woof")
assert d.speak() == "Rex says woof"
assert d.fetch() == "Rex fetches the ball!"

assert isinstance(a, Animal) == True
assert isinstance(d, Dog) == True
assert isinstance(d, Animal) == True
assert isinstance(a, Dog) == False

assert type(a) == Animal
assert type(d) == Dog

# Class variables
class Counter:
    count = 0

    def increment(self):
        self.count += 1

    def get(self):
        return self.count

c = Counter()
c.increment()
c.increment()
assert c.get() == 2

# Multiple classes, no inheritance
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance_sq(self):
        return self.x * self.x + self.y * self.y

p = Point(3, 4)
assert p.distance_sq() == 25

# Empty class
class Empty:
    pass

e = Empty()
assert isinstance(e, Empty) == True

print("classes ok")
