import ast
import sys
import pickle
import struct
from bytecode import (
    Writer,
    Executable,
    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FLOORDIV,
    OP_GT, OP_LT, OP_GTE, OP_LTE, OP_EQ, OP_NE,
    OP_STORE, OP_GET, OP_GET_ITER, OP_POP, OP_TERMINATE,
    OP_PUSH_CONST, OP_JMP, OP_JMP_IF_TRUE, OP_JMP_IF_FALSE,
    OP_MOD, OP_POW, OP_LSHIFT, OP_RSHIFT, OP_BITOR, OP_BITXOR, OP_BITAND,
    OP_CALL, OP_BUILD_LIST, OP_BUILD_TUPLE, OP_BUILD_SET, OP_BUILD_DICT, OP_FOR_ITER,
    OP_SUBSCRIPT, OP_GETATTR, OP_NEG, OP_POS, OP_NOT,
)

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
}

UNARY_MAP = {
    ast.USub: OP_NEG,
    ast.UAdd: OP_POS,
    ast.Not: OP_NOT,
}

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
            if node.keywords:
                raise NotImplementedError("Keyword arguments are not supported")
            if any(isinstance(a, ast.Starred) for a in node.args):
                raise NotImplementedError("Star arguments are not supported")
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

    def compile_stmts(self, stmts: list[ast.stmt], fallthrough_label: int):
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                    raise NotImplementedError("Only simple single-name assignments are supported")
                self._instr('push_const', stmt.targets[0].id)
                self.emit_expr(stmt.value)
                self._instr(OP_STORE)
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
                self.compile_stmts(stmt.body, header_label)
                self.emit_label(exit_label)
            elif isinstance(stmt, ast.For):
                if stmt.orelse:
                    raise NotImplementedError("for-else is not supported")
                if not isinstance(stmt.target, ast.Name):
                    raise NotImplementedError("Only simple name targets in for loops are supported")
                iter_var = f"__iter_{self.iter_count}__"
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
                self._instr('for_iter', stmt.target.id)
                self._instr('jmp_if_false', exit_label)
                self.compile_stmts(stmt.body, header_label)
                self.emit_label(exit_label)
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
