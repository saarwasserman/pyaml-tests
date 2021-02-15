import os
import sys
import json
import argparse

from importlib import import_module


def get_function_instance(project_name, funcion_str_rep):
    operation_str = funcion_str_rep
    split_operation_str = operation_str.split('.')

    module_name = '.'.join(['operations'] + split_operation_str[:-1])
    function_name = split_operation_str[-1]
    module_instance = import_module(module_name)
    function_instance = getattr(module_instance, function_name)
    return function_instance


def get_spec_data(results_dir, project, specid):
    with open(os.path.join(results_dir, project, specid, 'spec.json'), 'rb') as spec_json:
        spec_data = json.load(spec_json)
        json_formatted_str = json.dumps(spec_data, indent=2)
        print(json_formatted_str)


def main():
    parser = argparse.ArgumentParser(description='tests utils')
    parser.add_argument('--specid', type=str,
                        help='id of spec to get spec data of')
    parser.add_argument('--project', help='desired project to work on')

    args = parser.parse_args()
    if os.getenv('CI'):
        results_dir = '/automation/results'
    else:
        results_dir = '/tmp/results'

    if args.specid:
        get_spec_data(results_dir, args.project, args.specid)


if __name__ == "__main__":
    main()
