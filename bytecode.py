from typing import Optional
import struct

# encoding: each op is a single byte. If the op has a parameter
# the next byte is the parameter. If the parameter
# is 254, the real parameter is too big for a single byte
# and therefore was encoded in the next two. If the parameter was 255
# the parameter is encoded in the next four bytes.

TWO_BYTE_PARAM = 254
FOUR_BYTE_PARAM = 255

_next_availible_op = 1
def next_op():
    global _next_availible_op
    i = _next_availible_op
    _next_availible_op += 1
    return i

OP_ADD = next_op()
OP_SUB = next_op()
OP_MUL = next_op()
OP_DIV = next_op()
OP_FLOORDIV = next_op()
OP_MOD = next_op()
OP_POW = next_op()
OP_LSHIFT = next_op()
OP_RSHIFT = next_op()
OP_BITOR = next_op()
OP_BITXOR = next_op()
OP_BITAND = next_op()
OP_GT = next_op()
OP_LT = next_op()
OP_GTE = next_op()
OP_LTE = next_op()
OP_EQ = next_op()
OP_NE = next_op()
OP_STORE = next_op()    # pops name then value, stores in locals
OP_GET = next_op()      # pops name, pushes value (locals → globals → builtins)
OP_GET_ITER = next_op() # pops iterable, pushes iterator
OP_POP = next_op()         # discards TOS
OP_DUP = next_op()         # duplicates TOS
OP_RAISE = next_op()       # pops TOS and raises it as an exception
OP_DELETE_NAME = next_op() # pops name, deletes from locals
OP_TERMINATE = next_op()
OP_SUBSCRIPT = next_op()       # pops key then container, pushes container[key]
OP_STORE_SUBSCRIPT = next_op() # pops value, key, container; does container[key] = value
OP_GETATTR = next_op()         # pops name then obj, pushes getattr(obj, name)
OP_STORE_ATTR = next_op()      # pops value, name, obj; does setattr(obj, name, value)
OP_NEG = next_op()             # pops x, pushes -x
OP_POS = next_op()             # pops x, pushes +x
OP_NOT = next_op()             # pops x, pushes not x
OP_IS = next_op()              # pops b then a, pushes a is b
OP_IS_NOT = next_op()          # pops b then a, pushes a is not b
OP_RETURN = next_op()          # pops TOS and returns it from current function
OP_CALL_EX = next_op()         # pops kwargs dict, args list, callable; calls callable(*args, **kwargs)

# ops below here have a parameter
LAST_NO_PARAM_OP = OP_CALL_EX

OP_PUSH_CONST = next_op()    # param: constant-table index
OP_JMP = next_op()           # param: absolute byte offset
OP_JMP_IF_TRUE = next_op()   # param: absolute byte offset
OP_JMP_IF_FALSE = next_op()  # param: absolute byte offset
OP_CALL = next_op()          # param: number of positional args
OP_BUILD_LIST = next_op()    # param: number of elements
OP_BUILD_TUPLE = next_op()   # param: number of elements
OP_BUILD_SET = next_op()     # param: number of elements
OP_BUILD_DICT = next_op()    # param: number of key-value pairs
OP_FOR_ITER = next_op()      # param: constant-table index of loop-var name; pops iterator,
                             #        assigns next value to var and pushes True, or pushes False
OP_MAKE_FUNCTION = next_op() # param: constant-table index of FunctionSpec; pushes callable
OP_SUSPEND = next_op()       # param: number of args; pops args into tuple, suspends execution
OP_CALL_KW = next_op()       # param: number of positional args; pops kwargs dict, then pos args, then callable

class Executable:
    def __init__(self, buffer, constants  : dict[int, object]):
        self.buffer = bytes(buffer)
        self.constants= constants

class Writer:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.constants = {}

    def alloc_constant_index(self, value):
        # Key by (type, value) so that 1 and True (which compare equal)
        # get separate constant-table entries.
        key = (type(value), value)
        if key in self.constants:
            return self.constants[key]
        else:
            i = len(self.constants)
            self.constants[key] = i
            return i

    def add(self, op : int, param : Optional[int]):
        self.buffer.append(op)
        if param is not None:
            # todo: use more efficient encoding based on the value of param
            self.buffer.append(FOUR_BYTE_PARAM)
            self.buffer.extend(struct.pack(">i", param))

    def get_executable(self):
        return Executable(self.buffer, {i: v for (_, v), i in self.constants.items()})

class Reader:
    def __init__(self, buffer, pc):
        self.pc = pc
        self.buffer = buffer

    def next(self):
        op = self.buffer[self.pc]
        self.pc += 1
        param = None
        if op > LAST_NO_PARAM_OP:
            param = self.buffer[self.pc]
            self.pc += 1
            if param == TWO_BYTE_PARAM:
                param = struct.unpack(">h", self.buffer[self.pc: self.pc+2])[0]
                self.pc += 2
            elif param == FOUR_BYTE_PARAM:
                param = struct.unpack(">i", self.buffer[self.pc: self.pc+4])[0]
                self.pc += 4
        return op, param
