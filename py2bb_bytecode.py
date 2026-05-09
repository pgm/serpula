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
    OP_CALL, OP_BUILD_LIST, OP_BUILD_TUPLE, OP_BUILD_SET, OP_BUILD_DICT, OP_FOR_ITER,
    OP_SUBSCRIPT, OP_GETATTR, OP_NEG, OP_POS, OP_NOT,
)

BINOP_MAP = {
    ast.Add: OP_ADD,
    ast.Sub: OP_SUB,
    ast.Mult: OP_MUL,
    ast.Div: OP_DIV,
    ast.FloorDiv: OP_FLOORDIV,
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

# Abstract instruction format used before bytecode emission:
#   ('push_const', value)          — Python value; goes through constant table
#   ('for_iter', var_name)         — string var name; goes through constant table
#   ('jmp', block_idx)             — forward/backward jump; patched after layout
#   ('jmp_if_true', block_idx)     — conditional jump; patched after layout
#   ('jmp_if_false', block_idx)    — conditional jump; patched after layout
#   (op_code,)                     — no-param op
#   (op_code, int_param)           — param op with a plain integer (CALL, BUILD_LIST, etc.)


class Compiler:
    def __init__(self):
        self.blocks: dict[int, list] = {}
        self.next_idx = 0
        self.iter_count = 0

    def alloc_block(self) -> int:
        idx = self.next_idx
        self.next_idx += 1
        self.blocks[idx] = []
        return idx

    def _instr(self, block_idx: int, *instr):
        self.blocks[block_idx].append(instr)

    def emit_expr(self, node: ast.expr, block_idx: int):
        if isinstance(node, ast.Constant):
            self._instr(block_idx, 'push_const', node.value)
        elif isinstance(node, ast.Name):
            self._instr(block_idx, 'push_const', node.id)
            self._instr(block_idx, OP_GET)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in BINOP_MAP:
                raise NotImplementedError(f"Unsupported binary operator: {op_type.__name__}")
            self.emit_expr(node.left, block_idx)
            self.emit_expr(node.right, block_idx)
            self._instr(block_idx, BINOP_MAP[op_type])
        elif isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise NotImplementedError("Chained comparisons are not supported")
            op_type = type(node.ops[0])
            if op_type not in CMP_MAP:
                raise NotImplementedError(f"Unsupported comparison operator: {op_type.__name__}")
            self.emit_expr(node.left, block_idx)
            self.emit_expr(node.comparators[0], block_idx)
            self._instr(block_idx, CMP_MAP[op_type])
        elif isinstance(node, ast.Call):
            if node.keywords:
                raise NotImplementedError("Keyword arguments are not supported")
            if any(isinstance(a, ast.Starred) for a in node.args):
                raise NotImplementedError("Star arguments are not supported")
            self.emit_expr(node.func, block_idx)
            for arg in node.args:
                self.emit_expr(arg, block_idx)
            self._instr(block_idx, OP_CALL, len(node.args))
        elif isinstance(node, ast.Dict):
            if any(k is None for k in node.keys):
                raise NotImplementedError("Dict unpacking (**) is not supported")
            for key, value in zip(node.keys, node.values):
                assert key is not None
                self.emit_expr(key, block_idx)
                self.emit_expr(value, block_idx)
            self._instr(block_idx, OP_BUILD_DICT, len(node.keys))
        elif isinstance(node, ast.List):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only list literals in load context are supported")
            for elt in node.elts:
                self.emit_expr(elt, block_idx)
            self._instr(block_idx, OP_BUILD_LIST, len(node.elts))
        elif isinstance(node, ast.Tuple):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only tuple literals in load context are supported")
            for elt in node.elts:
                self.emit_expr(elt, block_idx)
            self._instr(block_idx, OP_BUILD_TUPLE, len(node.elts))
        elif isinstance(node, ast.Set):
            for elt in node.elts:
                self.emit_expr(elt, block_idx)
            self._instr(block_idx, OP_BUILD_SET, len(node.elts))
        elif isinstance(node, ast.Subscript):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only subscript in load context is supported")
            self.emit_expr(node.value, block_idx)
            self.emit_expr(node.slice, block_idx)
            self._instr(block_idx, OP_SUBSCRIPT)
        elif isinstance(node, ast.Attribute):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only attribute access in load context is supported")
            self.emit_expr(node.value, block_idx)
            self._instr(block_idx, 'push_const', node.attr)
            self._instr(block_idx, OP_GETATTR)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in UNARY_MAP:
                raise NotImplementedError(f"Unsupported unary operator: {op_type.__name__}")
            self.emit_expr(node.operand, block_idx)
            self._instr(block_idx, UNARY_MAP[op_type])
        else:
            raise NotImplementedError(f"Unsupported expression: {type(node).__name__}")

    def compile_stmts(self, stmts: list[ast.stmt], block_idx: int, fallthrough_idx: int):
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                    raise NotImplementedError("Only simple single-name assignments are supported")
                self._instr(block_idx, 'push_const', stmt.targets[0].id)
                self.emit_expr(stmt.value, block_idx)
                self._instr(block_idx, OP_STORE)
            elif isinstance(stmt, ast.Expr):
                self.emit_expr(stmt.value, block_idx)
                self._instr(block_idx, OP_POP)
            elif isinstance(stmt, ast.If):
                remaining = stmts[i + 1:]
                merge_block = self.alloc_block() if remaining else fallthrough_idx
                if remaining:
                    self.compile_stmts(remaining, merge_block, fallthrough_idx)
                true_block = self.alloc_block()
                false_block = self.alloc_block()
                self.emit_expr(stmt.test, block_idx)
                self._instr(block_idx, 'jmp_if_true', true_block)
                self._instr(block_idx, 'jmp', false_block)
                self.compile_stmts(stmt.body, true_block, merge_block)
                if stmt.orelse:
                    self.compile_stmts(stmt.orelse, false_block, merge_block)
                else:
                    self._instr(false_block, 'jmp', merge_block)
                return
            elif isinstance(stmt, ast.While):
                if stmt.orelse:
                    raise NotImplementedError("while-else is not supported")
                remaining = stmts[i + 1:]
                exit_block = self.alloc_block() if remaining else fallthrough_idx
                if remaining:
                    self.compile_stmts(remaining, exit_block, fallthrough_idx)
                header_block = self.alloc_block()
                body_block = self.alloc_block()
                self._instr(block_idx, 'jmp', header_block)
                self.emit_expr(stmt.test, header_block)
                self._instr(header_block, 'jmp_if_true', body_block)
                self._instr(header_block, 'jmp', exit_block)
                self.compile_stmts(stmt.body, body_block, header_block)
                return
            elif isinstance(stmt, ast.For):
                if stmt.orelse:
                    raise NotImplementedError("for-else is not supported")
                if not isinstance(stmt.target, ast.Name):
                    raise NotImplementedError("Only simple name targets in for loops are supported")
                target_name = stmt.target.id
                iter_var = f"__iter_{self.iter_count}__"
                self.iter_count += 1
                remaining = stmts[i + 1:]
                exit_block = self.alloc_block() if remaining else fallthrough_idx
                if remaining:
                    self.compile_stmts(remaining, exit_block, fallthrough_idx)
                header_block = self.alloc_block()
                body_block = self.alloc_block()
                self._instr(block_idx, 'push_const', iter_var)
                self.emit_expr(stmt.iter, block_idx)
                self._instr(block_idx, OP_GET_ITER)
                self._instr(block_idx, OP_STORE)
                self._instr(block_idx, 'jmp', header_block)
                self._instr(header_block, 'push_const', iter_var)
                self._instr(header_block, OP_GET)
                self._instr(header_block, 'for_iter', target_name)
                self._instr(header_block, 'jmp_if_true', body_block)
                self._instr(header_block, 'jmp', exit_block)
                self.compile_stmts(stmt.body, body_block, header_block)
                return
            else:
                raise NotImplementedError(f"Unsupported statement: {type(stmt).__name__}")
        self._instr(block_idx, 'jmp', fallthrough_idx)

    def compile(self, tree: ast.Module):
        start_block = self.alloc_block()
        terminate_block = self.alloc_block()
        self.blocks[terminate_block] = [(OP_TERMINATE,)]
        self.compile_stmts(tree.body, start_block, terminate_block)


def emit_bytecode(compiler: Compiler) -> Executable:
    writer = Writer()
    block_offsets: dict[int, int] = {}
    patch_list: list[tuple[int, int]] = []  # (byte offset of param to patch, target block idx)

    for block_idx in sorted(compiler.blocks):
        block_offsets[block_idx] = len(writer.buffer)
        for instr in compiler.blocks[block_idx]:
            op = instr[0]
            if op == 'push_const':
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

    for patch_offset, target_block in patch_list:
        struct.pack_into(">i", writer.buffer, patch_offset, block_offsets[target_block])

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
