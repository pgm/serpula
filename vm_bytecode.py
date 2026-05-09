import builtins as _builtins
import struct
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Frame:
    locals: dict = field(default_factory=dict)
    dstack: list = field(default_factory=list)
    prev_frame: Optional["Frame"] = None
    global_names: set = field(default_factory=set)

from bytecode import (
    Executable,
    TWO_BYTE_PARAM, FOUR_BYTE_PARAM, LAST_NO_PARAM_OP,
    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FLOORDIV,
    OP_MOD, OP_POW, OP_LSHIFT, OP_RSHIFT, OP_BITOR, OP_BITXOR, OP_BITAND,
    OP_GT, OP_LT, OP_GTE, OP_LTE, OP_EQ, OP_NE,
    OP_STORE, OP_GET, OP_GET_ITER, OP_POP, OP_DUP, OP_RAISE, OP_DELETE_NAME, OP_TERMINATE,
    OP_PUSH_CONST, OP_JMP, OP_JMP_IF_TRUE, OP_JMP_IF_FALSE,
    OP_CALL, OP_BUILD_LIST, OP_BUILD_TUPLE, OP_BUILD_SET, OP_BUILD_DICT, OP_FOR_ITER,
    OP_SUBSCRIPT, OP_STORE_SUBSCRIPT, OP_GETATTR, OP_STORE_ATTR, OP_NEG, OP_POS, OP_NOT,
    OP_IS, OP_IS_NOT, OP_RETURN, OP_MAKE_FUNCTION, OP_SUSPEND,
)

@dataclass
class Runtime:
    exe: Executable
    globals: dict = field(default_factory=dict)
    frame: Frame = field(default_factory=Frame)
    pc: int = 0
    suspended: bool = False
    suspend_value: object = None
    return_value: object = None

    def __post_init__(self):
        self.globals.setdefault('__builtins__', _builtins)


class FunctionSpec:
    """Compiled function body + metadata; stored in the constant table."""
    def __init__(self, exe: Executable, params: list[str], global_names: set[str]):
        self.exe = exe
        self.params = params
        self.global_names = global_names

    # FunctionSpec objects are used as constant-table keys via identity.
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


class SerpulaFunction:
    def __init__(self, spec: FunctionSpec, globals_dict: dict):
        self.spec = spec
        self.globals_dict = globals_dict

    def __call__(self, *args):
        if len(args) != len(self.spec.params):
            raise TypeError(
                f"expected {len(self.spec.params)} arguments, got {len(args)}"
            )
        frame = Frame(global_names=self.spec.global_names)
        for name, val in zip(self.spec.params, args):
            frame.locals[name] = val
        runtime = Runtime(exe=self.spec.exe, globals=self.globals_dict, frame=frame)
        result = execute(runtime)
        if result.suspended:
            raise RuntimeError("suspend inside a nested function call is not supported")
        return result.return_value


def execute(runtime: Runtime) -> Runtime:
    runtime.suspended = False
    buf = runtime.exe.buffer
    constants = runtime.exe.constants  # already {index: value}
    dstack = runtime.frame.dstack
    locals_ = runtime.frame.locals

    pc = runtime.pc
    while True:
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
        elif op == OP_RETURN:
            runtime.return_value = dstack.pop()
            break
        elif op == OP_SUSPEND:
            args = [dstack.pop() for _ in range(param)]
            args.reverse()
            runtime.suspend_value = tuple(args)
            runtime.suspended = True
            break
        elif op == OP_PUSH_CONST:
            dstack.append(constants[param])
        elif op == OP_GET:
            name = dstack.pop()
            _builtins_ns = runtime.globals['__builtins__']
            if name in runtime.frame.global_names:
                if name in runtime.globals:
                    dstack.append(runtime.globals[name])
                elif isinstance(_builtins_ns, dict):
                    dstack.append(_builtins_ns[name])
                else:
                    dstack.append(getattr(_builtins_ns, name))
            elif name in locals_:
                dstack.append(locals_[name])
            elif name in runtime.globals:
                dstack.append(runtime.globals[name])
            elif isinstance(_builtins_ns, dict):
                dstack.append(_builtins_ns[name])
            else:
                dstack.append(getattr(_builtins_ns, name))
        elif op == OP_STORE:
            value = dstack.pop()
            name = dstack.pop()
            if name in runtime.frame.global_names:
                runtime.globals[name] = value
            else:
                locals_[name] = value
        elif op == OP_POP:
            dstack.pop()
        elif op == OP_DUP:
            dstack.append(dstack[-1])
        elif op == OP_RAISE:
            raise dstack.pop()
        elif op == OP_DELETE_NAME:
            del locals_[dstack.pop()]
        elif op == OP_ADD:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a + b)
        elif op == OP_SUB:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a - b)
        elif op == OP_MUL:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a * b)
        elif op == OP_DIV:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a / b)
        elif op == OP_FLOORDIV:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a // b)
        elif op == OP_MOD:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a % b)
        elif op == OP_POW:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a ** b)
        elif op == OP_LSHIFT:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a << b)
        elif op == OP_RSHIFT:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a >> b)
        elif op == OP_BITOR:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a | b)
        elif op == OP_BITXOR:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a ^ b)
        elif op == OP_BITAND:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a & b)
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
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a == b)
        elif op == OP_NE:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a != b)
        elif op == OP_IS:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a is b)
        elif op == OP_IS_NOT:
            b = dstack.pop(); a = dstack.pop()
            dstack.append(a is not b)
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
        elif op == OP_STORE_SUBSCRIPT:
            value = dstack.pop(); key = dstack.pop(); container = dstack.pop()
            container[key] = value
        elif op == OP_GETATTR:
            name = dstack.pop()
            dstack.append(getattr(dstack.pop(), name))
        elif op == OP_STORE_ATTR:
            value = dstack.pop(); name = dstack.pop(); obj = dstack.pop()
            setattr(obj, name, value)
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
        elif op == OP_MAKE_FUNCTION:
            spec = constants[param]
            assert isinstance(spec, FunctionSpec)
            dstack.append(SerpulaFunction(spec, runtime.globals))
        else:
            raise RuntimeError(f"Unknown opcode {op} at pc={pc - 1}")

    runtime.pc = pc
    return runtime


def resume(runtime: Runtime, value: object) -> Runtime:
    if not runtime.suspended:
        raise RuntimeError("cannot resume a runtime that is not suspended")
    runtime.frame.dstack.append(value)
    return execute(runtime)
