# minipy

A toy Python compiler and VM with two execution backends: a basic-block interpreter and a bytecode interpreter.

## Files

### vm.py
The runtime. Defines:
- `Frame` — locals dict, data stack (`dstack`), parent frame pointer
- `VM` — globals dict + current Frame
- All VM operations as methods on `VM` (used directly by the basic-block backend and as the semantic reference for the bytecode backend):
  - Stack: `dpush`, `dpop`
  - Variables: `store` (pops name then value), `get` (pops name, resolves locals → globals → builtins)
  - Arithmetic: `add`, `sub`, `mul`, `div`, `floordiv`
  - Comparisons: `gt_cmp`, `lt_cmp`, `gte_cmp`, `lte_cmp`, `eq_cmp`, `ne_cmp`
  - Collections: `build_list(n)`, `build_dict(n)`
  - Iteration: `get_iter`, `for_iter(var_name)` (pops iterator, assigns next value to named local, pushes True/False)
  - Calls: `call(n)` (pops n args + callable, pushes result)
- `BasicBlock = Callable[[VM], int]` — a block returns the index of the next block, or `SUSPEND_BLOCK` (-1) to halt
- `run(vm, blocks, start_block)` — drives the basic-block interpreter

### bytecode.py
Bytecode encoding format and I/O classes.

**Encoding:** each instruction is 1 opcode byte. Ops above `LAST_NO_PARAM_OP` are followed by a parameter byte. If the parameter byte is 254 (`TWO_BYTE_PARAM`) the real parameter is the next 2 bytes (big-endian signed `h`). If 255 (`FOUR_BYTE_PARAM`) it is the next 4 bytes (big-endian signed `i`). Currently the `Writer` always uses the 4-byte form.

**No-param ops:** `OP_ADD`, `OP_SUB`, `OP_MUL`, `OP_DIV`, `OP_FLOORDIV`, `OP_GT`, `OP_LT`, `OP_GTE`, `OP_LTE`, `OP_EQ`, `OP_NE`, `OP_STORE`, `OP_GET`, `OP_GET_ITER`, `OP_POP`, `OP_TERMINATE`

**Param ops:**
- `OP_PUSH_CONST(idx)` — push `constants[idx]`
- `OP_JMP(offset)` — unconditional jump to absolute byte offset
- `OP_JMP_IF_TRUE(offset)` — pop TOS, jump if truthy
- `OP_JMP_IF_FALSE(offset)` — pop TOS, jump if falsy
- `OP_CALL(n)` — pop n args + callable, call, push result
- `OP_BUILD_LIST(n)` — pop n items, push list (preserving order)
- `OP_BUILD_DICT(n)` — pop n key-value pairs (interleaved), push dict
- `OP_FOR_ITER(idx)` — `constants[idx]` is the loop-var name; pops iterator, assigns next value to that local and pushes True, or pushes False on exhaustion

**Classes:**
- `Executable(buffer, constants)` — immutable: `buffer: bytes`, `constants: {index: value}` (already inverted by `Writer.get_executable()`; the interpreter uses it directly)
- `Writer` — mutable builder: `buffer: bytearray`, `constants: {value: index}`, `add(op, param)`, `alloc_constant_index(value)`, `get_executable() -> Executable`
- `Reader` — sequential decoder: `next() -> (op, param)`

### py2bb.py
Compiles a Python source file to a Python file containing basic-block functions (like `example.py`). Output is runnable Python.

**Compiler class:**
- `blocks: dict[int, list[str]]` — block index → list of Python code lines
- `alloc_block()` — allocates a new empty block, returns its index
- `emit_expr(node, lines)` — appends VM call strings for an expression onto `lines`
- `compile_stmts(stmts, block_idx, fallthrough_idx)` — compiles a statement list into a block; handles Assign, Expr, If, While, For; returns early after a control-flow statement (the fallthrough jump is embedded in the emitted strings)
- `compile(tree)` — entry point; allocates start block (idx 0) and terminate block (idx 1), then calls `compile_stmts`

**Supported Python:** assignments to simple names, `if`/`elif`/`else`, `while`, `for` (simple name target), binary ops (`+`, `-`, `*`, `/`, `//`), comparisons (`>`, `<`, `>=`, `<=`, `==`, `!=`), function calls (positional args only), list literals, dict literals. Anything else raises `NotImplementedError`.

**`for` loop implementation:** the iterator is stored in a synthetic local `__iter_N__`; the header block fetches it, calls `vm.for_iter('x')`, and branches on the pushed bool.

Usage: `python py2bb.py source.py` → prints a runnable Python file to stdout.

### py2bb_bytecode.py
Same compiler logic as `py2bb.py` but emits bytecode instead of Python source. Output is a pickled `Executable` written to stdout.

**Abstract IR** (intermediate between AST and bytecode emission):
- `('push_const', value)` — Python value, allocated into the constant table
- `('for_iter', var_name)` — string, allocated into the constant table
- `('jmp', block_idx)` / `('jmp_if_true', block_idx)` / `('jmp_if_false', block_idx)` — jump to block index; patched to byte offset in emission phase
- `(op_code,)` — no-param op
- `(op_code, int_param)` — param op with plain integer (e.g. `OP_CALL`, `OP_BUILD_LIST`)

**`emit_bytecode(compiler) -> Executable`:**
1. Emits all blocks in index order, recording each block's start byte offset
2. Jump instructions write a placeholder `0` and record `(buffer_offset_of_param, target_block_idx)` in a patch list
3. After all blocks are emitted, `struct.pack_into(">i", ...)` patches every placeholder with the real offset

Usage: `python py2bb_bytecode.py source.py > out.pkl`

### vm_bytecode.py
Bytecode interpreter.

**`execute(exe: Executable) -> VM`:**
- Creates a fresh `VM`
- Uses `exe.constants` directly (already `{index: value}`) for O(1) lookup
- Runs a `while True` fetch-decode-execute loop over `exe.buffer`
- All stack operations are inlined (no method calls) for speed
- Returns the `VM` after `OP_TERMINATE` so the caller can inspect `vm.frame.locals`

### example.py
Hand-written example of the basic-block format that `py2bb.py` generates. Compiles the snippet:
```python
a = 1; b = 2; c = a + b
if a > c: d = 1
else:     d = 2
```

## Data flow

```
source.py
    │
    ├─ py2bb.py ──────────────────────────► runnable_bb.py ──► vm.run()
    │                                        (basic blocks)
    │
    └─ py2bb_bytecode.py ──► out.pkl
                              (pickled Executable)
                                    │
                                    └─ vm_bytecode.execute() ──► VM (locals populated)
```
