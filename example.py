from vm import VM, SUSPEND_BLOCK, Terminate, run
"""
# original python
a = 1
b = 2
c = a + b
if a > c:
  d = 1
else: 
  d = 2
"""

def bb0(vm: VM):
    # a = 1
    vm.dpush("a")
    vm.dpush(1)
    vm.store()

    # b = 2
    vm.dpush("b")
    vm.dpush(2)
    vm.store()
    
    # c = a + b
    vm.dpush("c")
    vm.dpush("a")
    vm.get()
    vm.dpush("b")
    vm.get()
    vm.add()
    vm.store()

    vm.dpush("a")
    vm.get()
    vm.dpush("c")
    vm.get()
    vm.gt_cmp()
    if vm.dpop():
        return 1
    return 2

def bb1(vm:VM):
    # d = 1
    vm.dpush("d")
    vm.dpush(1)
    vm.store()
    return 3

def bb2(vm:VM):
    vm.dpush("d")
    vm.dpush(1)
    vm.store()
    return 3

def bb3(vm:VM):
    vm.dpush(Terminate())
    return SUSPEND_BLOCK


vm = VM()
blocks = [
    bb0,
    bb1,
    bb2,
    bb3
]
run(vm, blocks, 0)