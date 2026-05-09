# Implementation Plan

## Currently supported
- Assignments to simple names
- `if` / `elif` / `else`
- `while`
- `for` (simple name target)
- Binary ops: `+`, `-`, `*`, `/`, `//`
- Comparisons: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Function calls (positional args only)
- List literals
- Dict literals

## Implemented (Phase 1)

**Expressions**
- Subscript access: `a[0]`, `d["key"]`
- Attribute access: `obj.attr`
- Unary operators: `-x`, `+x`, `not x`

## Implemented (Phase 2)

**More expressions** 
- Tuple literals: `(1, 2, 3)`
- Set literals: `{1, 2, 3}`

## Implemented (Phase 2.1)
- Comprehensions: `[x for x in y]`, `{k: v for ...}`
- Also added remaining binary ops: `%`, `**`, `<<`, `>>`, `|`, `^`, `&`

## Implemented (Phase 3)
- Boolean operators: `and`, `or`

## Implemented (Phase 3.2)
- Conditional expression: `a if cond else b`

## To implement (Phase 3.5)
**Statements**
- Augmented assignment: `x += 1`

## To implement (Phase 3.6)
**Statements**
- Tuple unpacking: `a, b = 1, 2`

## To implement (Phase 3.7)
**Statements**
- `assert`
- `del`

## To implement (Phase 4)
- For loop with tuple target: `for i, j in pairs`
- `break` and `continue`

## To implement (Phase 5)
- `def` (function definitions)
- `global` / `nonlocal`
- `return` (function bodies)

## To implement (Phase 6)
- `import`

## To implement (Phase 7)
- Keyword and star args in calls: `f(x, key=val)`, `f(*args, **kwargs)`
- Lambda: `lambda x: x + 1`



## Will not implement
- Chained comparisons: `1 < x < 10`
- `try` / `except` / `finally`
- `with` (context managers)
- Classes (`class`, `self`, inheritance)
- Generators (`yield`)
- Decorators (`@`)
- `async` / `await`
- Walrus operator (`:=`)
- `match` / `case`
