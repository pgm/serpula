from dataclasses import dataclass
from typing import Any, Callable, Optional

@dataclass
class Terminate:
    pass

@dataclass
class Frame:
    locals : dict
    dstack : list
    prev_frame : Optional["Frame"]

default_globals = {"range": range, "len": len}

@dataclass
class VM:
    globals : dict
    frame : Frame

    def __init__(self) -> None:
        self.globals = dict(default_globals)
        self.frame = Frame(dstack=[], locals={}, prev_frame=None)

    def dpush(self, value):
        self.frame.dstack.append(value)

    def dpop(self):
        return self.frame.dstack.pop()
    
    ###

    def store(self):
        value = self.dpop()
        name = self.dpop()
        self.frame.locals[name] = value

    def get(self):
        import builtins
        name = self.dpop()
        if name in self.frame.locals:
            self.dpush(self.frame.locals[name])
        elif name in self.globals:
            self.dpush(self.globals[name])
        else:
            self.dpush(getattr(builtins, name))

    def call(self, n: int):
        args = [self.dpop() for _ in range(n)]
        args.reverse()
        func = self.dpop()
        self.dpush(func(*args))

    def get_iter(self):
        self.dpush(iter(self.dpop()))

    def for_iter(self, var_name: str):
        iterator = self.dpop()
        try:
            self.frame.locals[var_name] = next(iterator)
            self.dpush(True)
        except StopIteration:
            self.dpush(False)

    def subscript(self):
        key = self.dpop()
        container = self.dpop()
        self.dpush(container[key])

    def getattr_(self):
        name = self.dpop()
        obj = self.dpop()
        self.dpush(getattr(obj, name))

    def neg(self):
        self.dpush(-self.dpop())

    def pos(self):
        self.dpush(+self.dpop())

    def not_(self):
        self.dpush(not self.dpop())

    def build_list(self, n):
        items = [self.dpop() for _ in range(n)]
        self.dpush(items[::-1])

    def build_dict(self, n):
        pairs = [(self.dpop(), self.dpop()) for _ in range(n)]
        self.dpush({k: v for v, k in reversed(pairs)})

    def add(self):
        self.dpush(self.dpop() + self.dpop())   

    def sub(self):
        self.dpush(self.dpop() - self.dpop())

    def mul(self):
        self.dpush(self.dpop() * self.dpop())

    def div(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a / b)

    def floordiv(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a // b)

    def gt_cmp(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a > b)

    def lt_cmp(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a < b)

    def gte_cmp(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a >= b)

    def lte_cmp(self):
        b = self.dpop()
        a = self.dpop()
        self.dpush(a <= b)

    def eq_cmp(self):
        self.dpush(self.dpop() == self.dpop())

    def ne_cmp(self):
        self.dpush(self.dpop() != self.dpop())


BasicBlock = Callable[[VM], int]

SUSPEND_BLOCK = -1

def run(vm : VM, blocks : list[BasicBlock], start_block :int):
    cur_block = start_block
    while True:
        next_block = blocks[cur_block](vm)
        if next_block == SUSPEND_BLOCK:
            break
        cur_block = next_block
    return vm.dpop() # this is the object that describes why we suspended
