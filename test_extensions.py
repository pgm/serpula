"""
Tests for suspend/resume.
"""
import ast
from compiler import Compiler, emit_bytecode
from vm_bytecode import execute, resume, Runtime, Frame


def make_runtime(source: str, overrides: dict = {}) -> Runtime:
    tree = ast.parse(source)
    c = Compiler()
    c.compile(tree)
    globals_dict = dict(overrides)
    frame = Frame()
    frame.locals = globals_dict
    return Runtime(exe=emit_bytecode(c), globals=globals_dict, frame=frame)


def test_suspend_returns_args_as_tuple():
    rt = execute(make_runtime('suspend("a", "b", "c")'))
    assert rt.suspended
    assert rt.suspend_value == ("a", "b", "c")


def test_resume_provides_return_value():
    src = '''
x = suspend("a", "b", "c")
result = x[0] + x[1] + x[2]
'''
    rt = execute(make_runtime(src))
    assert rt.suspended
    assert rt.suspend_value == ("a", "b", "c")

    rt2 = resume(rt, ("a", "b", "c"))
    assert not rt2.suspended
    assert rt2.frame.locals["result"] == "abc"

def test_suspend_from_inside_a_call():
    rt = execute(make_runtime('''
def wrapper():
   suspend("a")
wrapper()
'''))
    assert rt.suspended
    assert rt.suspend_value == ("a",)

def test_resume_continues_after_suspend():
    src = '''
x = suspend(1)
y = suspend(2)
z = x[0] + y[0]
'''
    rt = execute(make_runtime(src))
    assert rt.suspended and rt.suspend_value == (1,)

    rt = resume(rt, (10,))
    assert rt.suspended and rt.suspend_value == (2,)

    rt = resume(rt, (20,))
    assert not rt.suspended
    assert rt.frame.locals["z"] == 30


def test_suspend_zero_args():
    rt = execute(make_runtime('suspend()'))
    assert rt.suspended
    assert rt.suspend_value == ()


def test_no_suspend_runs_to_completion():
    rt = execute(make_runtime('x = 1 + 2'))
    assert not rt.suspended
    assert rt.frame.locals["x"] == 3


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
