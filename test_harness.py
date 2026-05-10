import ast
from glob import glob
from compiler import Compiler, emit_bytecode
from vm_bytecode import execute, Runtime, Frame


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
    globals_dict = dict(overrides)
    frame = Frame()
    frame.locals = globals_dict
    runtime = Runtime(exe=emit_bytecode(compiler), globals=globals_dict, frame=frame)
    execute(runtime)

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
    
    serpula_out = OutputCollector()
    _run_via_bytecode(filename, {"print": serpula_out.output})

    # make sure the outputs from both match
    assert serpula_out.outputs == py_out.outputs

import logging
log = logging.getLogger(__name__)
def run_tests():
    success_count = 0
    failed_count = 0
    for filename in glob("examples/*.py"):
        try:
            exec_and_compare(filename)
            success_count += 1
        except Exception as ex:
            log.exception(f"test failed: {filename}")
            failed_count += 1
    print(f"{success_count} examples succeeded, {failed_count} failed")

if __name__ == "__main__":
    run_tests()