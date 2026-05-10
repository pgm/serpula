import ast
import sys
import pickle
import struct
from bytecode import (
    Writer,
    Executable,
    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FLOORDIV,
    OP_GT, OP_LT, OP_GTE, OP_LTE, OP_EQ, OP_NE,
    OP_STORE, OP_GET, OP_GET_ITER, OP_POP, OP_DUP, OP_RAISE, OP_DELETE_NAME, OP_TERMINATE,
    OP_PUSH_CONST, OP_JMP, OP_JMP_IF_TRUE, OP_JMP_IF_FALSE,
    OP_MOD, OP_POW, OP_LSHIFT, OP_RSHIFT, OP_BITOR, OP_BITXOR, OP_BITAND,
    OP_CALL, OP_BUILD_LIST, OP_BUILD_TUPLE, OP_BUILD_SET, OP_BUILD_DICT, OP_FOR_ITER,
    OP_SUBSCRIPT, OP_STORE_SUBSCRIPT, OP_GETATTR, OP_STORE_ATTR, OP_NEG, OP_POS, OP_NOT,
    OP_IS, OP_IS_NOT, OP_RETURN, OP_CALL_EX, OP_MAKE_FUNCTION, OP_SUSPEND, OP_CALL_KW,
)
from vm_bytecode import FunctionSpec

BINOP_MAP = {
    ast.Add: OP_ADD,
    ast.Sub: OP_SUB,
    ast.Mult: OP_MUL,
    ast.Div: OP_DIV,
    ast.FloorDiv: OP_FLOORDIV,
    ast.Mod: OP_MOD,
    ast.Pow: OP_POW,
    ast.LShift: OP_LSHIFT,
    ast.RShift: OP_RSHIFT,
    ast.BitOr: OP_BITOR,
    ast.BitXor: OP_BITXOR,
    ast.BitAnd: OP_BITAND,
}

CMP_MAP = {
    ast.Gt: OP_GT,
    ast.Lt: OP_LT,
    ast.GtE: OP_GTE,
    ast.LtE: OP_LTE,
    ast.Eq: OP_EQ,
    ast.NotEq: OP_NE,
    ast.Is: OP_IS,
    ast.IsNot: OP_IS_NOT,
}

UNARY_MAP = {
    ast.USub: OP_NEG,
    ast.UAdd: OP_POS,
    ast.Not: OP_NOT,
}

def _collect_globals(stmts: list[ast.stmt]) -> set[str]:
    """Collect all names declared global in stmts (non-recursively into nested defs)."""
    names: set[str] = set()
    for stmt in stmts:
        if isinstance(stmt, ast.Global):
            names.update(stmt.names)
        elif isinstance(stmt, ast.If):
            names.update(_collect_globals(stmt.body))
            names.update(_collect_globals(stmt.orelse))
        elif isinstance(stmt, (ast.While, ast.For)):
            names.update(_collect_globals(stmt.body))
        # Do not recurse into nested FunctionDef bodies
    return names


# Flat linear IR emitted into self.ir before bytecode generation:
#   ('label', label_id)            — marks a branch target; no bytecode emitted
#   ('push_const', value)          — Python value; allocated into constant table
#   ('for_iter', var_name)         — string var name; allocated into constant table
#   ('jmp', label_id)              — unconditional jump; patched to byte offset
#   ('jmp_if_true', label_id)      — conditional jump; patched to byte offset
#   ('jmp_if_false', label_id)     — conditional jump; patched to byte offset
#   (op_code,)                     — no-param op
#   (op_code, int_param)           — param op with plain integer (CALL, BUILD_LIST, etc.)


class Compiler:
    def __init__(self):
        self.ir: list[tuple] = []
        self.next_label = 0
        self.iter_count = 0
        self.comp_count = 0
        self.loop_stack: list[tuple[int, int]] = []  # (header_label, exit_label)

    def alloc_label(self) -> int:
        label = self.next_label
        self.next_label += 1
        return label

    def emit_label(self, label: int):
        self.ir.append(('label', label))

    def _instr(self, *instr):
        self.ir.append(instr)

    def emit_expr(self, node: ast.expr):
        if isinstance(node, ast.Constant):
            self._instr('push_const', node.value)
        elif isinstance(node, ast.Name):
            self._instr('push_const', node.id)
            self._instr(OP_GET)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in BINOP_MAP:
                raise NotImplementedError(f"Unsupported binary operator: {op_type.__name__}")
            self.emit_expr(node.left)
            self.emit_expr(node.right)
            self._instr(BINOP_MAP[op_type])
        elif isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise NotImplementedError("Chained comparisons are not supported")
            op_type = type(node.ops[0])
            if op_type not in CMP_MAP:
                raise NotImplementedError(f"Unsupported comparison operator: {op_type.__name__}")
            self.emit_expr(node.left)
            self.emit_expr(node.comparators[0])
            self._instr(CMP_MAP[op_type])
        elif isinstance(node, ast.Call):
            has_starred = any(isinstance(a, ast.Starred) for a in node.args)
            has_dstar = any(kw.arg is None for kw in node.keywords)
            if isinstance(node.func, ast.Name) and node.func.id == 'suspend':
                if has_starred or has_dstar:
                    raise NotImplementedError("star args not supported in suspend()")
                for arg in node.args:
                    self.emit_expr(arg)
                self._instr(OP_SUSPEND, len(node.args))
            elif has_starred or has_dstar:
                # evaluate func first (stays at bottom of dstack)
                self.emit_expr(node.func)
                # build positional args list in a temp var using append/extend
                list_var = f"__args_{self.iter_count}__"
                self.iter_count += 1
                self._instr('push_const', list_var)
                self._instr(OP_BUILD_LIST, 0)
                self._instr(OP_STORE)
                for arg in node.args:
                    self._instr('push_const', list_var)
                    self._instr(OP_GET)
                    if isinstance(arg, ast.Starred):
                        self._instr('push_const', 'extend')
                        self._instr(OP_GETATTR)
                        self.emit_expr(arg.value)
                    else:
                        self._instr('push_const', 'append')
                        self._instr(OP_GETATTR)
                        self.emit_expr(arg)
                    self._instr(OP_CALL, 1)
                    self._instr(OP_POP)
                # build kwargs dict in a temp var using setitem/update
                kw_var = f"__kwargs_{self.iter_count}__"
                self.iter_count += 1
                self._instr('push_const', kw_var)
                self._instr(OP_BUILD_DICT, 0)
                self._instr(OP_STORE)
                for kw in node.keywords:
                    self._instr('push_const', kw_var)
                    self._instr(OP_GET)
                    if kw.arg is None:
                        self._instr('push_const', 'update')
                        self._instr(OP_GETATTR)
                        self.emit_expr(kw.value)
                        self._instr(OP_CALL, 1)
                        self._instr(OP_POP)
                    else:
                        self._instr('push_const', kw.arg)
                        self.emit_expr(kw.value)
                        self._instr(OP_STORE_SUBSCRIPT)
                # stack: [func]; push args list and kwargs dict then call
                self._instr('push_const', list_var)
                self._instr(OP_GET)
                self._instr('push_const', kw_var)
                self._instr(OP_GET)
                self._instr(OP_CALL_EX)
            elif node.keywords:
                self.emit_expr(node.func)
                for arg in node.args:
                    self.emit_expr(arg)
                for kw in node.keywords:
                    self._instr('push_const', kw.arg)
                    self.emit_expr(kw.value)
                self._instr(OP_BUILD_DICT, len(node.keywords))
                self._instr(OP_CALL_KW, len(node.args))
            else:
                self.emit_expr(node.func)
                for arg in node.args:
                    self.emit_expr(arg)
                self._instr(OP_CALL, len(node.args))
        elif isinstance(node, ast.Dict):
            if any(k is None for k in node.keys):
                raise NotImplementedError("Dict unpacking (**) is not supported")
            for key, value in zip(node.keys, node.values):
                assert key is not None
                self.emit_expr(key)
                self.emit_expr(value)
            self._instr(OP_BUILD_DICT, len(node.keys))
        elif isinstance(node, ast.List):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only list literals in load context are supported")
            for elt in node.elts:
                self.emit_expr(elt)
            self._instr(OP_BUILD_LIST, len(node.elts))
        elif isinstance(node, ast.Tuple):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only tuple literals in load context are supported")
            for elt in node.elts:
                self.emit_expr(elt)
            self._instr(OP_BUILD_TUPLE, len(node.elts))
        elif isinstance(node, ast.Set):
            for elt in node.elts:
                self.emit_expr(elt)
            self._instr(OP_BUILD_SET, len(node.elts))
        elif isinstance(node, ast.Subscript):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only subscript in load context is supported")
            self.emit_expr(node.value)
            self.emit_expr(node.slice)
            self._instr(OP_SUBSCRIPT)
        elif isinstance(node, ast.Attribute):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only attribute access in load context is supported")
            self.emit_expr(node.value)
            self._instr('push_const', node.attr)
            self._instr(OP_GETATTR)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in UNARY_MAP:
                raise NotImplementedError(f"Unsupported unary operator: {op_type.__name__}")
            self.emit_expr(node.operand)
            self._instr(UNARY_MAP[op_type])
        elif isinstance(node, ast.BoolOp):
            end_label = self.alloc_label()
            is_and = isinstance(node.op, ast.And)
            for i, value in enumerate(node.values):
                self.emit_expr(value)
                if i < len(node.values) - 1:
                    self._instr(OP_DUP)
                    self._instr('jmp_if_false' if is_and else 'jmp_if_true', end_label)
                    self._instr(OP_POP)
            self.emit_label(end_label)
        elif isinstance(node, ast.IfExp):
            else_label = self.alloc_label()
            end_label = self.alloc_label()
            self.emit_expr(node.test)
            self._instr('jmp_if_false', else_label)
            self.emit_expr(node.body)
            self._instr('jmp', end_label)
            self.emit_label(else_label)
            self.emit_expr(node.orelse)
            self.emit_label(end_label)
        elif isinstance(node, ast.ListComp):
            result_var = f"__comp_{self.comp_count}__"
            self.comp_count += 1
            self._instr('push_const', result_var)
            self._instr(OP_BUILD_LIST, 0)
            self._instr(OP_STORE)
            def _list_elt(n=node, rv=result_var):
                self._instr('push_const', rv); self._instr(OP_GET)
                self._instr('push_const', 'append'); self._instr(OP_GETATTR)
                self.emit_expr(n.elt)
                self._instr(OP_CALL, 1); self._instr(OP_POP)
            self._emit_gen_loop(node.generators, 0, _list_elt)
            self._instr('push_const', result_var)
            self._instr(OP_GET)
        elif isinstance(node, ast.SetComp):
            result_var = f"__comp_{self.comp_count}__"
            self.comp_count += 1
            self._instr('push_const', result_var)
            self._instr(OP_BUILD_SET, 0)
            self._instr(OP_STORE)
            def _set_elt(n=node, rv=result_var):
                self._instr('push_const', rv); self._instr(OP_GET)
                self._instr('push_const', 'add'); self._instr(OP_GETATTR)
                self.emit_expr(n.elt)
                self._instr(OP_CALL, 1); self._instr(OP_POP)
            self._emit_gen_loop(node.generators, 0, _set_elt)
            self._instr('push_const', result_var)
            self._instr(OP_GET)
        elif isinstance(node, ast.DictComp):
            result_var = f"__comp_{self.comp_count}__"
            self.comp_count += 1
            self._instr('push_const', result_var)
            self._instr(OP_BUILD_DICT, 0)
            self._instr(OP_STORE)
            def _dict_elt(n=node, rv=result_var):
                self._instr('push_const', rv); self._instr(OP_GET)
                self._instr('push_const', '__setitem__'); self._instr(OP_GETATTR)
                self.emit_expr(n.key)
                self.emit_expr(n.value)
                self._instr(OP_CALL, 2); self._instr(OP_POP)
            self._emit_gen_loop(node.generators, 0, _dict_elt)
            self._instr('push_const', result_var)
            self._instr(OP_GET)
        else:
            raise NotImplementedError(f"Unsupported expression: {type(node).__name__}")

    def _emit_gen_loop(self, generators: list, idx: int, on_element):
        gen = generators[idx]
        if not isinstance(gen.target, ast.Name):
            raise NotImplementedError("Only simple name targets in comprehensions are supported")
        if gen.is_async:
            raise NotImplementedError("Async comprehensions are not supported")
        iter_var = f"__iter_{self.iter_count}__"
        self.iter_count += 1
        header_label = self.alloc_label()
        exit_label = self.alloc_label()
        self._instr('push_const', iter_var)
        self.emit_expr(gen.iter)
        self._instr(OP_GET_ITER)
        self._instr(OP_STORE)
        self.emit_label(header_label)
        self._instr('push_const', iter_var)
        self._instr(OP_GET)
        self._instr('for_iter', gen.target.id)
        self._instr('jmp_if_false', exit_label)
        for cond in gen.ifs:
            self.emit_expr(cond)
            self._instr('jmp_if_false', header_label)
        if idx + 1 < len(generators):
            self._emit_gen_loop(generators, idx + 1, on_element)
        else:
            on_element()
        self._instr('jmp', header_label)
        self.emit_label(exit_label)

    def _compile_class_body(self, stmts: list[ast.stmt], ns_var: str):
        for stmt in stmts:
            if isinstance(stmt, ast.Pass):
                pass
            elif isinstance(stmt, ast.FunctionDef):
                if stmt.decorator_list:
                    raise NotImplementedError("Decorators are not supported")
                args = stmt.args
                if args.kwonlyargs or args.kw_defaults:
                    raise NotImplementedError("Keyword-only parameters are not supported")
                params = [arg.arg for arg in args.args]
                vararg = args.vararg.arg if args.vararg else None
                kwarg = args.kwarg.arg if args.kwarg else None
                n_defaults = len(args.defaults)
                global_names = _collect_globals(stmt.body)
                for default_node in args.defaults:
                    self.emit_expr(default_node)
                func_compiler = Compiler()
                func_terminate_label = func_compiler.alloc_label()
                func_compiler.compile_stmts(stmt.body, func_terminate_label)
                func_compiler.emit_label(func_terminate_label)
                func_compiler._instr('push_const', None)
                func_compiler._instr(OP_RETURN)
                func_exe = emit_bytecode(func_compiler)
                spec = FunctionSpec(func_exe, params, global_names, n_defaults, vararg, kwarg)
                # ns_var[method_name] = SerpulaFunction(spec)
                self._instr('push_const', ns_var)
                self._instr(OP_GET)
                self._instr('push_const', stmt.name)
                self._instr('make_function', spec)
                self._instr(OP_STORE_SUBSCRIPT)
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                if isinstance(stmt, ast.Assign):
                    targets = stmt.targets
                    value_node = stmt.value
                else:
                    if stmt.value is None:
                        continue
                    targets = [stmt.target]
                    value_node = stmt.value
                for target in targets:
                    if not isinstance(target, ast.Name):
                        raise NotImplementedError("Only simple name targets in class body assignments")
                    self._instr('push_const', ns_var)
                    self._instr(OP_GET)
                    self._instr('push_const', target.id)
                    self.emit_expr(value_node)
                    self._instr(OP_STORE_SUBSCRIPT)
            else:
                raise NotImplementedError(f"Unsupported statement in class body: {type(stmt).__name__}")

    def emit_assignment(self, target: ast.expr, emit_value):
        """Emit code to store a value into target. emit_value() pushes the value onto the stack."""
        if isinstance(target, ast.Name):
            self._instr('push_const', target.id)
            emit_value()
            self._instr(OP_STORE)
        elif isinstance(target, ast.Subscript):
            self.emit_expr(target.value)
            self.emit_expr(target.slice)
            emit_value()
            self._instr(OP_STORE_SUBSCRIPT)
        elif isinstance(target, ast.Attribute):
            self.emit_expr(target.value)
            self._instr('push_const', target.attr)
            emit_value()
            self._instr(OP_STORE_ATTR)
        elif isinstance(target, (ast.Tuple, ast.List)):
            temp_var = f"__unpack_{self.iter_count}__"
            self.iter_count += 1
            self._instr('push_const', temp_var)
            emit_value()
            self._instr(OP_STORE)
            for i, elt in enumerate(target.elts):
                idx = i
                self.emit_assignment(elt, lambda i=idx, v=temp_var: (
                    self._instr('push_const', v),
                    self._instr(OP_GET),
                    self._instr('push_const', i),
                    self._instr(OP_SUBSCRIPT),
                ))
        else:
            raise NotImplementedError(f"Unsupported assignment target: {type(target).__name__}")

    def compile_stmts(self, stmts: list[ast.stmt], fallthrough_label: int):
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                # Evaluate value once into a temp if there are multiple targets
                if len(stmt.targets) > 1:
                    temp_var = f"__assign_{self.iter_count}__"
                    self.iter_count += 1
                    self._instr('push_const', temp_var)
                    self.emit_expr(stmt.value)
                    self._instr(OP_STORE)
                    for target in stmt.targets:
                        self.emit_assignment(target, lambda v=temp_var: (
                            self._instr('push_const', v), self._instr(OP_GET)))
                else:
                    value_node = stmt.value
                    self.emit_assignment(stmt.targets[0], lambda v=value_node: self.emit_expr(v))
            elif isinstance(stmt, ast.AnnAssign):
                # Type annotation — ignore the annotation, compile value if present
                if stmt.value is not None and isinstance(stmt.target, ast.Name):
                    value_node = stmt.value
                    self.emit_assignment(stmt.target, lambda v=value_node: self.emit_expr(v))
            elif isinstance(stmt, ast.AugAssign):
                op_type = type(stmt.op)
                if op_type not in BINOP_MAP:
                    raise NotImplementedError(f"Unsupported augmented assignment operator: {op_type.__name__}")
                if isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    self._instr('push_const', name)  # for store
                    self._instr('push_const', name)  # for load
                    self._instr(OP_GET)
                    self.emit_expr(stmt.value)
                    self._instr(BINOP_MAP[op_type])
                    self._instr(OP_STORE)
                elif isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name):
                    obj_name = stmt.target.value.id
                    attr_name = stmt.target.attr
                    # push obj and attr name for OP_STORE_ATTR at end
                    self._instr('push_const', obj_name)
                    self._instr(OP_GET)
                    self._instr('push_const', attr_name)
                    # compute old op rhs
                    self._instr('push_const', obj_name)
                    self._instr(OP_GET)
                    self._instr('push_const', attr_name)
                    self._instr(OP_GETATTR)
                    self.emit_expr(stmt.value)
                    self._instr(BINOP_MAP[op_type])
                    # stack: [obj, attr_name, new_value]
                    self._instr(OP_STORE_ATTR)
                else:
                    raise NotImplementedError("Only simple name or obj.attr targets are supported for augmented assignment")
            elif isinstance(stmt, ast.Assert):
                end_label = self.alloc_label()
                self.emit_expr(stmt.test)
                self._instr('jmp_if_true', end_label)
                self._instr('push_const', 'AssertionError')
                self._instr(OP_GET)
                if stmt.msg:
                    self.emit_expr(stmt.msg)
                    self._instr(OP_CALL, 1)
                else:
                    self._instr(OP_CALL, 0)
                self._instr(OP_RAISE)
                self.emit_label(end_label)
            elif isinstance(stmt, ast.Delete):
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        raise NotImplementedError("Only simple name targets are supported for del")
                    self._instr('push_const', target.id)
                    self._instr(OP_DELETE_NAME)
            elif isinstance(stmt, ast.Expr):
                self.emit_expr(stmt.value)
                self._instr(OP_POP)
            elif isinstance(stmt, ast.If):
                false_label = self.alloc_label()
                merge_label = self.alloc_label()
                self.emit_expr(stmt.test)
                self._instr('jmp_if_false', false_label)
                self.compile_stmts(stmt.body, merge_label)
                self.emit_label(false_label)
                if stmt.orelse:
                    self.compile_stmts(stmt.orelse, merge_label)
                self.emit_label(merge_label)
            elif isinstance(stmt, ast.While):
                if stmt.orelse:
                    raise NotImplementedError("while-else is not supported")
                header_label = self.alloc_label()
                exit_label = self.alloc_label()
                self.emit_label(header_label)
                self.emit_expr(stmt.test)
                self._instr('jmp_if_false', exit_label)
                self.loop_stack.append((header_label, exit_label))
                self.compile_stmts(stmt.body, header_label)
                self.loop_stack.pop()
                self.emit_label(exit_label)
            elif isinstance(stmt, ast.For):
                if stmt.orelse:
                    raise NotImplementedError("for-else is not supported")
                iter_var = f"__iter_{self.iter_count}__"
                self.iter_count += 1
                if isinstance(stmt.target, ast.Name):
                    target_var = stmt.target.id
                else:
                    target_var = f"__for_target_{self.iter_count}__"
                    self.iter_count += 1
                header_label = self.alloc_label()
                exit_label = self.alloc_label()
                self._instr('push_const', iter_var)
                self.emit_expr(stmt.iter)
                self._instr(OP_GET_ITER)
                self._instr(OP_STORE)
                self.emit_label(header_label)
                self._instr('push_const', iter_var)
                self._instr(OP_GET)
                self._instr('for_iter', target_var)
                self._instr('jmp_if_false', exit_label)
                if not isinstance(stmt.target, ast.Name):
                    tv = target_var
                    self.emit_assignment(stmt.target, lambda v=tv: (
                        self._instr('push_const', v), self._instr(OP_GET)))
                self.loop_stack.append((header_label, exit_label))
                self.compile_stmts(stmt.body, header_label)
                self.loop_stack.pop()
                self.emit_label(exit_label)
            elif isinstance(stmt, ast.Break):
                if not self.loop_stack:
                    raise SyntaxError("break outside loop")
                self._instr('jmp', self.loop_stack[-1][1])
            elif isinstance(stmt, ast.Continue):
                if not self.loop_stack:
                    raise SyntaxError("continue outside loop")
                self._instr('jmp', self.loop_stack[-1][0])
            elif isinstance(stmt, ast.FunctionDef):
                if stmt.decorator_list:
                    raise NotImplementedError("Decorators are not supported")
                args = stmt.args
                if args.kwonlyargs or args.kw_defaults:
                    raise NotImplementedError("Keyword-only parameters are not supported")
                params = [arg.arg for arg in args.args]
                vararg = args.vararg.arg if args.vararg else None
                kwarg = args.kwarg.arg if args.kwarg else None
                n_defaults = len(args.defaults)
                global_names = _collect_globals(stmt.body)
                # emit default expressions before make_function so VM can pop them
                for default_node in args.defaults:
                    self.emit_expr(default_node)
                func_compiler = Compiler()
                func_terminate_label = func_compiler.alloc_label()
                func_compiler.compile_stmts(stmt.body, func_terminate_label)
                func_compiler.emit_label(func_terminate_label)
                func_compiler._instr('push_const', None)
                func_compiler._instr(OP_RETURN)
                func_exe = emit_bytecode(func_compiler)
                spec = FunctionSpec(func_exe, params, global_names, n_defaults, vararg, kwarg)
                self._instr('push_const', stmt.name)
                self._instr('make_function', spec)
                self._instr(OP_STORE)
            elif isinstance(stmt, ast.Return):
                if stmt.value is not None:
                    self.emit_expr(stmt.value)
                else:
                    self._instr('push_const', None)
                self._instr(OP_RETURN)
            elif isinstance(stmt, ast.Global):
                pass  # names already collected at FunctionDef compilation time
            elif isinstance(stmt, ast.Nonlocal):
                raise NotImplementedError("nonlocal is not supported")
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    store_name = alias.asname if alias.asname else alias.name.split('.')[0]
                    self._instr('push_const', store_name)
                    self._instr('push_const', '__import__')
                    self._instr(OP_GET)
                    self._instr('push_const', alias.name)
                    self._instr('push_const', None)  # globals
                    self._instr('push_const', None)  # locals
                    self._instr(OP_BUILD_LIST, 0)    # fromlist
                    self._instr('push_const', 0)     # level
                    self._instr(OP_CALL, 5)
                    # dotted import with alias: traverse attributes to get the leaf module
                    if alias.asname and '.' in alias.name:
                        for attr in alias.name.split('.')[1:]:
                            self._instr('push_const', attr)
                            self._instr(OP_GETATTR)
                    self._instr(OP_STORE)
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.level != 0:
                    raise NotImplementedError("Relative imports are not supported")
                if any(alias.name == '*' for alias in stmt.names):
                    raise NotImplementedError("from foo import * is not supported")
                fromlist = [alias.name for alias in stmt.names]
                temp_var = f"__import_{self.iter_count}__"
                self.iter_count += 1
                self._instr('push_const', temp_var)
                self._instr('push_const', '__import__')
                self._instr(OP_GET)
                self._instr('push_const', stmt.module)
                self._instr('push_const', None)  # globals
                self._instr('push_const', None)  # locals
                for name in fromlist:
                    self._instr('push_const', name)
                self._instr(OP_BUILD_LIST, len(fromlist))
                self._instr('push_const', 0)     # level
                self._instr(OP_CALL, 5)
                self._instr(OP_STORE)
                for alias in stmt.names:
                    store_name = alias.asname if alias.asname else alias.name
                    self._instr('push_const', store_name)
                    self._instr('push_const', temp_var)
                    self._instr(OP_GET)
                    self._instr('push_const', alias.name)
                    self._instr(OP_GETATTR)
                    self._instr(OP_STORE)
            elif isinstance(stmt, ast.Pass):
                pass
            elif isinstance(stmt, ast.ClassDef):
                if stmt.decorator_list:
                    raise NotImplementedError("Class decorators are not supported")
                if stmt.keywords:
                    raise NotImplementedError("Metaclasses are not supported")
                ns_var = f"__cls_ns_{self.iter_count}__"
                self.iter_count += 1
                # initialise namespace dict
                self._instr('push_const', ns_var)
                self._instr(OP_BUILD_DICT, 0)
                self._instr(OP_STORE)
                # compile class body into the namespace dict
                self._compile_class_body(stmt.body, ns_var)
                # push store-target name first, then call type(name, bases, ns)
                self._instr('push_const', stmt.name)
                self._instr('push_const', 'type')
                self._instr(OP_GET)
                self._instr('push_const', stmt.name)
                for base in stmt.bases:
                    self.emit_expr(base)
                self._instr(OP_BUILD_TUPLE, len(stmt.bases))
                self._instr('push_const', ns_var)
                self._instr(OP_GET)
                self._instr(OP_CALL, 3)
                # stack: [class_name, class_obj] → OP_STORE
                self._instr(OP_STORE)
            else:
                raise NotImplementedError(f"Unsupported statement: {type(stmt).__name__}")
        self._instr('jmp', fallthrough_label)

    def compile(self, tree: ast.Module):
        terminate_label = self.alloc_label()
        self.compile_stmts(tree.body, terminate_label)
        self.emit_label(terminate_label)
        self._instr(OP_TERMINATE)


def emit_bytecode(compiler: Compiler) -> Executable:
    writer = Writer()
    label_offsets: dict[int, int] = {}
    patch_list: list[tuple[int, int]] = []  # (byte offset of param to patch, target label)

    for instr in compiler.ir:
        op = instr[0]
        if op == 'label':
            label_offsets[instr[1]] = len(writer.buffer)
        elif op == 'push_const':
            writer.add(OP_PUSH_CONST, writer.alloc_constant_index(instr[1]))
        elif op == 'for_iter':
            writer.add(OP_FOR_ITER, writer.alloc_constant_index(instr[1]))
        elif op == 'make_function':
            writer.add(OP_MAKE_FUNCTION, writer.alloc_constant_index(instr[1]))
        elif op in ('jmp', 'jmp_if_true', 'jmp_if_false'):
            real_op = {'jmp': OP_JMP, 'jmp_if_true': OP_JMP_IF_TRUE, 'jmp_if_false': OP_JMP_IF_FALSE}[op]
            patch_list.append((len(writer.buffer) + 2, instr[1]))
            writer.add(real_op, 0)  # placeholder offset
        elif len(instr) == 1:
            writer.add(op, None)
        else:
            writer.add(op, instr[1])

    for patch_offset, target_label in patch_list:
        struct.pack_into(">i", writer.buffer, patch_offset, label_offsets[target_label])

    return writer.get_executable()


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <source.py>", file=sys.stderr)
        sys.exit(1)
    source_file = sys.argv[1]
    with open(source_file) as f:
        source = f.read()
    tree = ast.parse(source, filename=source_file)
    compiler = Compiler()
    compiler.compile(tree)
    writer = emit_bytecode(compiler)
    sys.stdout.buffer.write(pickle.dumps(writer))


if __name__ == "__main__":
    main()
