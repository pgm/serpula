# minipy

A toy Python compiler targeting a custom stack-based bytecode VM. Compiles a subset of Python via the `ast` module into a flat bytecode buffer and executes it with a fetch-decode-execute loop.

## Files

### bytecode.py
Opcode definitions, bytecode encoding format, and I/O classes.

**Encoding:** each instruction is 1 opcode byte. Ops above `LAST_NO_PARAM_OP` are followed by a parameter byte. If the parameter byte is 254 (`TWO_BYTE_PARAM`) the real parameter is the next 2 bytes (big-endian signed `h`). If 255 (`FOUR_BYTE_PARAM`) it is the next 4 bytes (big-endian signed `i`). The `Writer` always uses the 4-byte form.

**No-param ops:**
`OP_ADD`, `OP_SUB`, `OP_MUL`, `OP_DIV`, `OP_FLOORDIV`, `OP_MOD`, `OP_POW`,
`OP_LSHIFT`, `OP_RSHIFT`, `OP_BITOR`, `OP_BITXOR`, `OP_BITAND`,
`OP_GT`, `OP_LT`, `OP_GTE`, `OP_LTE`, `OP_EQ`, `OP_NE`, `OP_IS`, `OP_IS_NOT`,
`OP_STORE`, `OP_GET`, `OP_GET_ITER`, `OP_POP`, `OP_DUP`, `OP_RAISE`, `OP_DELETE_NAME`, `OP_TERMINATE`,
`OP_SUBSCRIPT`, `OP_STORE_SUBSCRIPT`, `OP_GETATTR`, `OP_STORE_ATTR`,
`OP_NEG`, `OP_POS`, `OP_NOT`, `OP_RETURN`

**Param ops:**
- `OP_PUSH_CONST(idx)` — push `constants[idx]`
- `OP_JMP(offset)` — unconditional jump to absolute byte offset
- `OP_JMP_IF_TRUE(offset)` — pop TOS, jump if truthy
- `OP_JMP_IF_FALSE(offset)` — pop TOS, jump if falsy
- `OP_CALL(n)` — pop n args then callable, call, push result
- `OP_BUILD_LIST(n)` — pop n items, push list (preserving push order)
- `OP_BUILD_TUPLE(n)` — pop n items, push tuple (preserving push order)
- `OP_BUILD_SET(n)` — pop n items, push set
- `OP_BUILD_DICT(n)` — pop n interleaved key-value pairs, push dict
- `OP_FOR_ITER(idx)` — `constants[idx]` is the loop-var name; pops iterator, assigns next value to that local and pushes True, or pushes False on exhaustion
- `OP_MAKE_FUNCTION(idx)` — `constants[idx]` is a `FunctionSpec`; wraps it in a `MiniPyFunction` and pushes it
- `OP_SUSPEND(n)` — pop n args into a tuple, save the program counter, and halt execution (see [Suspend/Resume](#suspendresume))

**Classes:**
- `Executable(buffer, constants)` — immutable: `buffer: bytes`, `constants: {index: value}` (already inverted by `Writer.get_executable()`; the interpreter uses it directly)
- `Writer` — mutable builder: `add(op, param)`, `alloc_constant_index(value)`, `get_executable() -> Executable`
- `Reader` — sequential decoder: `next() -> (op, param)`

### py2bb_bytecode.py
Compiles Python source to an `Executable`.

**`Compiler` class** emits a flat linear IR:
- `('label', id)` — branch target; no bytecode emitted
- `('push_const', value)` — allocated into the constant table
- `('for_iter', var_name)` — allocated into the constant table
- `('jmp', label)` / `('jmp_if_true', label)` / `('jmp_if_false', label)` — patched to absolute byte offset
- `('make_function', spec)` — allocated into the constant table
- `(op_code,)` — no-param op
- `(op_code, int_param)` — param op with a plain integer

**`emit_bytecode(compiler) -> Executable`:**
Single pass over the IR: records label offsets, emits opcodes, then patches all jump placeholders with `struct.pack_into`.

**`Compiler.compile(tree)`** — entry point; takes a parsed `ast.Module`.

Usage: `python py2bb_bytecode.py source.py > out.pkl`

### vm_bytecode.py
Bytecode interpreter and execution model.

**`Frame`** — per-call state: `locals` dict, `dstack` (data stack), `global_names` (set of names declared `global`).

**`Runtime`** — the complete execution state passed to `execute` and `resume`:
- `exe: Executable` — the bytecode being executed
- `globals: dict` — module-level namespace (shared by reference across all calls)
- `frame: Frame` — current frame
- `pc: int` — program counter (updated on every exit, including suspend)
- `suspended: bool` — True if execution stopped at `OP_SUSPEND`
- `suspend_value: object` — the tuple of args passed to `suspend(...)`, when suspended
- `return_value: object` — the value from `return`, when a function returned

**`execute(runtime: Runtime) -> Runtime`** — runs the fetch-decode-execute loop from `runtime.pc`. Returns when it hits `OP_TERMINATE`, `OP_RETURN`, or `OP_SUSPEND`.

**`resume(runtime: Runtime, value: object) -> Runtime`** — pushes `value` onto the dstack (making it the "return value" of the suspended `suspend(...)` call) and re-enters `execute` from the saved pc.

**`FunctionSpec`** — compiled function metadata stored in the constant table: `exe`, `params`, `global_names`. Uses identity-based `__hash__`/`__eq__` so it is a valid constant-table key.

**`MiniPyFunction`** — callable that captures a `FunctionSpec` and the current globals dict. On call, creates a fresh `Frame`, populates it with arguments, runs a nested `execute`, and returns `runtime.return_value`.

At module level, `frame.locals` must be set to the same dict as `globals` before calling `execute` (so that top-level definitions are visible to functions as globals). The test harness and any other entry-point callers are responsible for this setup.

### test_harness.py
Runs every `examples/*.py` file through both the real Python interpreter (`exec`) and the minipy compiler+VM, and asserts that their `print` outputs match.

### test_extensions.py
Tests for the `suspend`/`resume` extension (see below).

## Supported Python

### Expressions
- Literals: integers, floats, strings, booleans, `None`
- List, tuple, set, and dict literals
- Binary ops: `+`, `-`, `*`, `/`, `//`, `%`, `**`, `<<`, `>>`, `|`, `^`, `&`
- Comparison ops: `>`, `<`, `>=`, `<=`, `==`, `!=`, `is`, `is not`
- Boolean ops: `and`, `or`
- Unary ops: `-`, `+`, `not`
- Conditional expression: `a if cond else b`
- Subscript access: `a[i]`
- Attribute access: `obj.attr`
- Function calls (positional args only): `f(a, b)`
- Comprehensions: list `[x for x in y if cond]`, set `{...}`, dict `{k: v ...}`

### Statements
- Assignment: `x = expr`, multiple targets (`a = b = expr`), tuple unpacking (`a, b = expr`)
- Augmented assignment: `x += 1` (simple name targets only)
- Annotated assignment: `x: int = expr` (annotation is ignored)
- L-value forms: `x[i] = v`, `obj.attr = v`, `x.a.b = v`, `a, b = expr`
- `if` / `elif` / `else`
- `while` (no `else`)
- `for` with simple name or tuple target (no `else`)
- `break` / `continue`
- `assert`
- `del` (simple names only)
- `def` — function definitions with positional parameters; `return`; implicit `return None`
- `global` — names are routed through the globals dict in both reads and writes
- Type annotations (`x: int = ...`) — annotation is parsed but ignored

### Not supported
`nonlocal`, `try`/`except`/`finally`, `with`, `class`, `yield`/generators, decorators, `async`/`await`, walrus operator (`:=`), `match`/`case`, chained comparisons (`1 < x < 10`), keyword/star args, lambda, `import`.

## Suspend/Resume

minipy adds a non-standard `suspend` built-in that allows execution to be paused and later resumed — similar in spirit to coroutines, but driven explicitly by the host.

### How it works

`suspend(arg1, arg2, ...)` is a special syntactic form (not a real callable). The compiler detects calls to the bare name `suspend` and emits `OP_SUSPEND` instead of `OP_CALL`. When the VM hits `OP_SUSPEND` it:

1. Pops the arguments off the data stack and packages them as a tuple.
2. Saves the current program counter (pointing just past the `OP_SUSPEND` instruction).
3. Sets `runtime.suspended = True` and `runtime.suspend_value = tuple(args)`.
4. Returns from `execute`.

`resume(runtime, value)` re-enters execution:
1. Pushes `value` onto the data stack — this becomes the value that `x = suspend(...)` evaluates to.
2. Calls `execute(runtime)` from the saved pc.

### Example

```python
import ast
from py2bb_bytecode import Compiler, emit_bytecode
from vm_bytecode import execute, resume, Runtime, Frame

source = """
x = suspend("query", "arg")
result = x[0] + ":" + x[1]
"""

tree = ast.parse(source)
c = Compiler()
c.compile(tree)

globals_dict = {}
frame = Frame()
frame.locals = globals_dict
runtime = Runtime(exe=emit_bytecode(c), globals=globals_dict, frame=frame)

rt = execute(runtime)
assert rt.suspended
assert rt.suspend_value == ("query", "arg")

# host does some work, then resumes with a value
rt = resume(rt, ("answer",))
assert not rt.suspended
assert rt.frame.locals["result"] == "answer:arg"
```

Multiple `suspend` calls in a single script work naturally — each `resume` runs the program until the next `suspend` or until it finishes.

## Data flow

```
source.py
    │
    └─ py2bb_bytecode.py (Compiler + emit_bytecode)
            │
            └─ Executable (buffer: bytes, constants: {index: value})
                    │
                    └─ vm_bytecode.execute(Runtime)
                            │
                            ├─ normal exit  → runtime.return_value / locals populated
                            └─ OP_SUSPEND   → runtime.suspended = True, runtime.suspend_value set
                                                    │
                                                    └─ vm_bytecode.resume(runtime, value) ──► ...
```
