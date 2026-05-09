import ast
from glob import glob
from py2bb_bytecode import Compiler, emit_bytecode
from vm_bytecode import execute


def _run_via_python(filename: str, overrides: dict):
    with open(filename) as f:
        source = f.read()
    exec(source, dict(overrides))


def _run_via_bytecode(filename: str, overrides: dict):
    with open(filename) as f:
        source = f.read()
    tree = ast.parse(source, filename=filename)
    compiler = Compiler()
    compiler.compile(tree)
    execute(emit_bytecode(compiler), globals=overrides)

class OutputCollector:
    def __init__(self) -> None:
        self.outputs = []

    def output(self, value):
        self.outputs.append(value)

def exec_and_compare(filename : str):
    # define a function which will be used to emit data such that 
    # we can compare outputs from two runs
    
    py_out = OutputCollector()
    _run_via_python(filename, {"print": py_out.output})
    
    mini_py_out = OutputCollector()
    _run_via_bytecode(filename, {"print": mini_py_out.output})

    # make sure the outputs from both match
    assert mini_py_out.outputs == py_out.outputs


def run_tests():
    for filename in glob("examples/*.py"):
        exec_and_compare(filename)
