import ast
import sys

BINOP_MAP = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.FloorDiv: "floordiv",
}

CMP_MAP = {
    ast.Gt: "gt_cmp",
    ast.Lt: "lt_cmp",
    ast.GtE: "gte_cmp",
    ast.LtE: "lte_cmp",
    ast.Eq: "eq_cmp",
    ast.NotEq: "ne_cmp",
}


class Compiler:
    def __init__(self):
        self.blocks: dict[int, list[str]] = {}
        self.next_idx = 0
        self.iter_count = 0

    def alloc_block(self) -> int:
        idx = self.next_idx
        self.next_idx += 1
        self.blocks[idx] = []
        return idx

    def emit_expr(self, node: ast.expr, lines: list[str]):
        if isinstance(node, ast.Constant):
            lines.append(f"    vm.dpush({repr(node.value)})")
        elif isinstance(node, ast.Name):
            lines.append(f"    vm.dpush({repr(node.id)})")
            lines.append(f"    vm.get()")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in BINOP_MAP:
                raise NotImplementedError(f"Unsupported binary operator: {op_type.__name__}")
            self.emit_expr(node.left, lines)
            self.emit_expr(node.right, lines)
            lines.append(f"    vm.{BINOP_MAP[op_type]}()")
        elif isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise NotImplementedError("Chained comparisons are not supported")
            op_type = type(node.ops[0])
            if op_type not in CMP_MAP:
                raise NotImplementedError(f"Unsupported comparison operator: {op_type.__name__}")
            self.emit_expr(node.left, lines)
            self.emit_expr(node.comparators[0], lines)
            lines.append(f"    vm.{CMP_MAP[op_type]}()")
        elif isinstance(node, ast.Call):
            if node.keywords:
                raise NotImplementedError("Keyword arguments are not supported")
            if any(isinstance(a, ast.Starred) for a in node.args):
                raise NotImplementedError("Star arguments are not supported")
            self.emit_expr(node.func, lines)
            for arg in node.args:
                self.emit_expr(arg, lines)
            lines.append(f"    vm.call({len(node.args)})")
        elif isinstance(node, ast.Dict):
            if any(k is None for k in node.keys):
                raise NotImplementedError("Dict unpacking (**) is not supported")
            for key, value in zip(node.keys, node.values):
                assert key is not None
                self.emit_expr(key, lines)
                self.emit_expr(value, lines)
            lines.append(f"    vm.build_dict({len(node.keys)})")
        elif isinstance(node, ast.List):
            if not isinstance(node.ctx, ast.Load):
                raise NotImplementedError("Only list literals in load context are supported")
            for elt in node.elts:
                self.emit_expr(elt, lines)
            lines.append(f"    vm.build_list({len(node.elts)})")
        else:
            raise NotImplementedError(f"Unsupported expression: {type(node).__name__}")

    def compile_stmts(self, stmts: list[ast.stmt], block_idx: int, fallthrough_idx: int):
        lines = self.blocks[block_idx]
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                    raise NotImplementedError("Only simple single-name assignments are supported")
                target_name = stmt.targets[0].id
                lines.append(f"    # {ast.unparse(stmt)}")
                lines.append(f"    vm.dpush({repr(target_name)})")
                self.emit_expr(stmt.value, lines)
                lines.append(f"    vm.store()")
            elif isinstance(stmt, ast.Expr):
                self.emit_expr(stmt.value, lines)
                lines.append(f"    vm.dpop()")
            elif isinstance(stmt, ast.If):
                remaining = stmts[i + 1:]
                if remaining:
                    merge_block = self.alloc_block()
                    self.compile_stmts(remaining, merge_block, fallthrough_idx)
                else:
                    merge_block = fallthrough_idx
                true_block = self.alloc_block()
                false_block = self.alloc_block()
                self.emit_expr(stmt.test, lines)
                lines.append(f"    if vm.dpop():")
                lines.append(f"        return {true_block}")
                lines.append(f"    return {false_block}")
                self.compile_stmts(stmt.body, true_block, merge_block)
                if stmt.orelse:
                    self.compile_stmts(stmt.orelse, false_block, merge_block)
                else:
                    self.blocks[false_block].append(f"    return {merge_block}")
                return
            elif isinstance(stmt, ast.While):
                if stmt.orelse:
                    raise NotImplementedError("while-else is not supported")
                remaining = stmts[i + 1:]
                if remaining:
                    exit_block = self.alloc_block()
                    self.compile_stmts(remaining, exit_block, fallthrough_idx)
                else:
                    exit_block = fallthrough_idx
                header_block = self.alloc_block()
                body_block = self.alloc_block()
                lines.append(f"    return {header_block}")
                header_lines = self.blocks[header_block]
                self.emit_expr(stmt.test, header_lines)
                header_lines.append(f"    if vm.dpop():")
                header_lines.append(f"        return {body_block}")
                header_lines.append(f"    return {exit_block}")
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
                if remaining:
                    exit_block = self.alloc_block()
                    self.compile_stmts(remaining, exit_block, fallthrough_idx)
                else:
                    exit_block = fallthrough_idx
                header_block = self.alloc_block()
                body_block = self.alloc_block()
                lines.append(f"    vm.dpush({repr(iter_var)})")
                self.emit_expr(stmt.iter, lines)
                lines.append(f"    vm.get_iter()")
                lines.append(f"    vm.store()")
                lines.append(f"    return {header_block}")
                header_lines = self.blocks[header_block]
                header_lines.append(f"    vm.dpush({repr(iter_var)})")
                header_lines.append(f"    vm.get()")
                header_lines.append(f"    vm.for_iter({repr(target_name)})")
                header_lines.append(f"    if vm.dpop():")
                header_lines.append(f"        return {body_block}")
                header_lines.append(f"    return {exit_block}")
                self.compile_stmts(stmt.body, body_block, header_block)
                return
            else:
                raise NotImplementedError(f"Unsupported statement: {type(stmt).__name__}")
        lines.append(f"    return {fallthrough_idx}")

    def compile(self, tree: ast.Module):
        start_block = self.alloc_block()
        terminate_block = self.alloc_block()
        self.blocks[terminate_block] = [
            "    vm.dpush(Terminate())",
            "    return SUSPEND_BLOCK",
        ]
        self.compile_stmts(tree.body, start_block, terminate_block)


def generate(compiler: Compiler, source: str) -> str:
    lines = [
        "from vm import VM, SUSPEND_BLOCK, Terminate, run",
        "",
        '"""',
        "# original python:",
    ]
    for src_line in source.splitlines():
        lines.append(f"# {src_line}")
    lines.append('"""')
    lines.append("")
    for idx in sorted(compiler.blocks):
        lines.append(f"def bb{idx}(vm: VM):")
        block_lines = compiler.blocks[idx]
        lines.extend(block_lines if block_lines else ["    pass"])
        lines.append("")
    lines.append("vm = VM()")
    lines.append("blocks = [")
    for idx in sorted(compiler.blocks):
        lines.append(f"    bb{idx},")
    lines.append("]")
    lines.append("run(vm, blocks, 0)")
    lines.append("")
    return "\n".join(lines)


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
    print(generate(compiler, source))


if __name__ == "__main__":
    main()
