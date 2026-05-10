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
    OP_IS, OP_IS_NOT, OP_RETURN, OP_CALL_EX, OP_MAKE_FUNCTION, OP_SUSPEND, OP_CALL_KW,
)
# Not exposed — require custom implementation to work correctly in serpula:
#   compile(), eval(), exec(), globals(), locals()

import builtins as _builtins

exceptions = {
    # Exceptions (looked up by name at runtime, e.g. by assert and raise)
    'ArithmeticError':      _builtins.ArithmeticError,
    'AssertionError':       _builtins.AssertionError,
    'AttributeError':       _builtins.AttributeError,
    'BaseException':        _builtins.BaseException,
    'EOFError':             _builtins.EOFError,
    'Exception':            _builtins.Exception,
    'FileNotFoundError':    _builtins.FileNotFoundError,
    'FloatingPointError':   _builtins.FloatingPointError,
    'GeneratorExit':        _builtins.GeneratorExit,
    'IOError':              _builtins.IOError,
    'ImportError':          _builtins.ImportError,
    'IndexError':           _builtins.IndexError,
    'InterruptedError':     _builtins.InterruptedError,
    'IsADirectoryError':    _builtins.IsADirectoryError,
    'KeyError':             _builtins.KeyError,
    'KeyboardInterrupt':    _builtins.KeyboardInterrupt,
    'LookupError':          _builtins.LookupError,
    'MemoryError':          _builtins.MemoryError,
    'NameError':            _builtins.NameError,
    'NotADirectoryError':   _builtins.NotADirectoryError,
    'NotImplementedError':  _builtins.NotImplementedError,
    'OSError':              _builtins.OSError,
    'OverflowError':        _builtins.OverflowError,
    'PermissionError':      _builtins.PermissionError,
    'ProcessLookupError':   _builtins.ProcessLookupError,
    'RecursionError':       _builtins.RecursionError,
    'RuntimeError':         _builtins.RuntimeError,
    'StopIteration':        _builtins.StopIteration,
    'SyntaxError':          _builtins.SyntaxError,
    'SystemExit':           _builtins.SystemExit,
    'TimeoutError':         _builtins.TimeoutError,
    'TypeError':            _builtins.TypeError,
    'UnboundLocalError':    _builtins.UnboundLocalError,
    'UnicodeError':         _builtins.UnicodeError,
    'ValueError':           _builtins.ValueError,
    'ZeroDivisionError':    _builtins.ZeroDivisionError,
    # Constants
    'NotImplemented':       _builtins.NotImplemented,
    'Ellipsis':             _builtins.Ellipsis,
}

default_builtins = {
    # Functions safe to delegate to the native Python version
    'getattr':      _builtins.getattr,
    'hasattr':      _builtins.hasattr,
    'abs':          _builtins.abs,
    'all':          _builtins.all,
    'any':          _builtins.any,
    'ascii':        _builtins.ascii,
    'bin':          _builtins.bin,
    'bool':         _builtins.bool,
    'bytearray':    _builtins.bytearray,
    'bytes':        _builtins.bytes,
    'callable':     _builtins.callable,
    'chr':          _builtins.chr,
    'complex':      _builtins.complex,
    'delattr':      _builtins.delattr,
    'dict':         _builtins.dict,
    'dir':          _builtins.dir,
    'divmod':       _builtins.divmod,
    'enumerate':    _builtins.enumerate,
    'filter':       _builtins.filter,
    'float':        _builtins.float,
    'format':       _builtins.format,
    'frozenset':    _builtins.frozenset,
    'hash':         _builtins.hash,
    'hex':          _builtins.hex,
    'id':           _builtins.id,
    'input':        _builtins.input,
    'int':          _builtins.int,
    'isinstance':   _builtins.isinstance,
    'issubclass':   _builtins.issubclass,
    'iter':         _builtins.iter,
    'len':          _builtins.len,
    'list':         _builtins.list,
    'map':          _builtins.map,
    'max':          _builtins.max,
    'memoryview':   _builtins.memoryview,
    'min':          _builtins.min,
    'next':         _builtins.next,
    'object':       _builtins.object,
    'oct':          _builtins.oct,
    'open':         _builtins.open,
    'ord':          _builtins.ord,
    'pow':          _builtins.pow,
    'print':        _builtins.print,
    'property':     _builtins.property,
    'range':        _builtins.range,
    'repr':         _builtins.repr,
    'reversed':     _builtins.reversed,
    'round':        _builtins.round,
    'set':          _builtins.set,
    'setattr':      _builtins.setattr,
    'slice':        _builtins.slice,
    'sorted':       _builtins.sorted,
    'str':          _builtins.str,
    'sum':          _builtins.sum,
    'super':        _builtins.super,
    'tuple':        _builtins.tuple,
    'type':         _builtins.type,
    'vars':         _builtins.vars,
    'zip':          _builtins.zip,
    '__debug__':            __debug__,
}

default_builtins.update(exceptions)

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
        self.globals.setdefault('__builtins__', default_builtins)


class FunctionSpec:
    """Compiled function body + metadata; stored in the constant table."""
    def __init__(self, exe: Executable, params: list[str], global_names: set[str],
                 n_defaults: int = 0, vararg: str | None = None, kwarg: str | None = None):
        self.exe = exe
        self.params = params
        self.global_names = global_names
        self.n_defaults = n_defaults
        self.vararg = vararg  # name of *args parameter, or None
        self.kwarg = kwarg    # name of **kwargs parameter, or None

    # FunctionSpec objects are used as constant-table keys via identity.
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


class SerpulaFunction:
    def __init__(self, spec: FunctionSpec, globals_dict: dict, defaults: dict):
        self.spec = spec
        self.globals_dict = globals_dict
        self.defaults = defaults  # {param_name: default_value}, evaluated at def time

    def __call__(self, *args, **kwargs):
        params = self.spec.params
        vararg = self.spec.vararg
        kwarg_name = self.spec.kwarg
        frame_locals: dict = {}
        # bind positional args to regular params
        for name, val in zip(params, args):
            frame_locals[name] = val
        # extra positional args go to *args
        extra_pos = args[len(params):]
        if extra_pos and vararg is None:
            raise TypeError(f"too many positional arguments")
        if vararg is not None:
            frame_locals[vararg] = tuple(extra_pos)
        # bind keyword args
        param_set = set(params)
        extra_kwargs: dict = {}
        for name, val in kwargs.items():
            if name in param_set:
                if name in frame_locals:
                    raise TypeError(f"got multiple values for argument '{name}'")
                frame_locals[name] = val
            elif kwarg_name is not None:
                extra_kwargs[name] = val
            else:
                raise TypeError(f"unexpected keyword argument '{name}'")
        if kwarg_name is not None:
            frame_locals[kwarg_name] = extra_kwargs
        for name, val in self.defaults.items():
            if name not in frame_locals:
                frame_locals[name] = val
        for name in params:
            if name not in frame_locals:
                raise TypeError(f"missing required argument '{name}'")
        frame = Frame(global_names=self.spec.global_names)
        frame.locals = frame_locals
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
            defaults = {}
            if spec.n_defaults > 0:
                vals = [dstack.pop() for _ in range(spec.n_defaults)]
                vals.reverse()
                default_params = spec.params[len(spec.params) - spec.n_defaults:]
                defaults = dict(zip(default_params, vals))
            dstack.append(SerpulaFunction(spec, runtime.globals, defaults))
        elif op == OP_CALL_EX:
            kwargs = dstack.pop()
            args = dstack.pop()
            func = dstack.pop()
            dstack.append(func(*args, **kwargs))
        elif op == OP_CALL_KW:
            kwargs = dstack.pop()
            args = [dstack.pop() for _ in range(param)]
            args.reverse()
            func = dstack.pop()
            dstack.append(func(*args, **kwargs))
        else:
            raise RuntimeError(f"Unknown opcode {op} at pc={pc - 1}")

    runtime.pc = pc
    return runtime


def resume(runtime: Runtime, value: object) -> Runtime:
    if not runtime.suspended:
        raise RuntimeError("cannot resume a runtime that is not suspended")
    runtime.frame.dstack.append(value)
    return execute(runtime)
