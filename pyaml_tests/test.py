
import os

from importlib import import_module

from .utils import get_function_instance

def test(spec):

    operation_str = spec['operation']
    project_name = spec['project']

    function_instance = get_function_instance(project_name, operation_str)
    function_instance(spec)


# future feature run against multiple workers
def test_using_queue():
    pass
