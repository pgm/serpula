import builtins as _builtins
import struct
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Frame:
    locals: dict = field(default_factory=dict)
    dstack: list = field(default_factory=list)
    prev_frame: Optional["Frame"] = None

@dataclass
class VM:
    globals: dict = field(default_factory=dict)
    frame: Frame = field(default_factory=Frame)

from bytecode import (
    Executable,
    TWO_BYTE_PARAM, FOUR_BYTE_PARAM, LAST_NO_PARAM_OP,
    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FLOORDIV,
    OP_GT, OP_LT, OP_GTE, OP_LTE, OP_EQ, OP_NE,
    OP_STORE, OP_GET, OP_GET_ITER, OP_POP, OP_TERMINATE,
    OP_PUSH_CONST, OP_JMP, OP_JMP_IF_TRUE, OP_JMP_IF_FALSE,
    OP_CALL, OP_BUILD_LIST, OP_BUILD_TUPLE, OP_BUILD_SET, OP_BUILD_DICT, OP_FOR_ITER,
    OP_SUBSCRIPT, OP_GETATTR, OP_NEG, OP_POS, OP_NOT,
)

def execute(exe: Executable, globals: Optional[dict] = None) -> VM:
    vm = VM()
    if globals:
        vm.globals.update(globals)
    buf = exe.buffer
    constants = exe.constants  # already {index: value}
    dstack = vm.frame.dstack
    locals_ = vm.frame.locals

    pc = 0
    while True:
        assert isinstance(buf, bytes)
        assert isinstance(pc, int)
        op = buf[pc]
        pc += 1

        param: int = 0
        if op > LAST_NO_PARAM_OP:
            b = buf[pc]
            pc += 1
            if b == TWO_BYTE_PARAM:
                param = struct.unpack(">h", buf[pc:pc + 2])[0]
                pc += 2
            elif b == FOUR_BYTE_PARAM:
                param = struct.unpack(">i", buf[pc:pc + 4])[0]
                pc += 4
            else:
                param = b

        if op == OP_TERMINATE:
            break
        elif op == OP_PUSH_CONST:
            dstack.append(constants[param])
        elif op == OP_GET:
            name = dstack.pop()
            if name in locals_:
                dstack.append(locals_[name])
            elif name in vm.globals:
                dstack.append(vm.globals[name])
            else:
                dstack.append(getattr(_builtins, name))
        elif op == OP_STORE:
            value = dstack.pop()
            name = dstack.pop()
            locals_[name] = value
        elif op == OP_POP:
            dstack.pop()
        elif op == OP_ADD:
            dstack.append(dstack.pop() + dstack.pop())
        elif op == OP_SUB:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a - b)
        elif op == OP_MUL:
            dstack.append(dstack.pop() * dstack.pop())
        elif op == OP_DIV:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a / b)
        elif op == OP_FLOORDIV:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a // b)
        elif op == OP_GT:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a > b)
        elif op == OP_LT:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a < b)
        elif op == OP_GTE:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a >= b)
        elif op == OP_LTE:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a <= b)
        elif op == OP_EQ:
            dstack.append(dstack.pop() == dstack.pop())
        elif op == OP_NE:
            dstack.append(dstack.pop() != dstack.pop())
        elif op == OP_GET_ITER:
            dstack.append(iter(dstack.pop()))
        elif op == OP_FOR_ITER:
            var_name = constants[param]
            iterator = dstack.pop()
            try:
                locals_[var_name] = next(iterator)
                dstack.append(True)
            except StopIteration:
                dstack.append(False)
        elif op == OP_BUILD_LIST:
            items = [dstack.pop() for _ in range(param)]
            dstack.append(items[::-1])
        elif op == OP_BUILD_TUPLE:
            items = [dstack.pop() for _ in range(param)]
            dstack.append(tuple(items[::-1]))
        elif op == OP_BUILD_SET:
            items = [dstack.pop() for _ in range(param)]
            dstack.append(set(items))
        elif op == OP_BUILD_DICT:
            pairs = [(dstack.pop(), dstack.pop()) for _ in range(param)]
            dstack.append({k: v for v, k in reversed(pairs)})
        elif op == OP_CALL:
            args = [dstack.pop() for _ in range(param)]
            args.reverse()
            func = dstack.pop()
            dstack.append(func(*args))
        elif op == OP_SUBSCRIPT:
            key = dstack.pop()
            dstack.append(dstack.pop()[key])
        elif op == OP_GETATTR:
            name = dstack.pop()
            dstack.append(getattr(dstack.pop(), name))
        elif op == OP_NEG:
            dstack.append(-dstack.pop())
        elif op == OP_POS:
            dstack.append(+dstack.pop())
        elif op == OP_NOT:
            dstack.append(not dstack.pop())
        elif op == OP_JMP:
            pc = param
        elif op == OP_JMP_IF_TRUE:
            if dstack.pop():
                pc = param
        elif op == OP_JMP_IF_FALSE:
            if not dstack.pop():
                pc = param
        else:
            raise RuntimeError(f"Unknown opcode {op} at pc={pc - 1}")

    return vm
