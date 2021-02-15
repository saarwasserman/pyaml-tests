import os
import sys
import json
import random
import copy
import glob
import logging
import collections.abc
import pytest


from datetime import datetime
from uuid import uuid4
from pathlib import Path

import yaml

from pyaml_tests.config import get_config
from pyaml_tests.utils import get_function_instance

logger = logging.getLogger(__file__)


# ignore collection from following files - framework using specific convntions - see docs
collect_ignore = ["setup.py"]
if sys.version_info[0] > 2:
    collect_ignore.append("tests/*.py")


def pytest_addoption(parser):
    """optional arguments for the pytest command"""

    # dev options
    parser.addoption('--build_dir', default='', help='dev base output directory')

    # collection types
    parser.addoption('--include', default=[], nargs='*', help='include tests based on their attributes')
    parser.addoption('--exclude', default=[], nargs='*', help='exclude tests based on their attributes')
    parser.addoption('--specs', nargs='*', help='list of path to spec.json files re-production')
    parser.addoption('--modules', nargs='*', help='paths to yaml files to run e.g. passes.yaml')
    parser.addoption('--tests', nargs='*', help='list of testnames spec.test')
    parser.addoption('--project', default='', help='project name to run test for')


def pytest_generate_tests(metafunc):
    """ selects and generates tests from specs based on given cli args """

    build_config = get_config(metafunc.config)
    project_name = metafunc.config.getoption('--project')

    # export PYTHONPATH={TO OPERATIONS DIR IN THE SPECIFIED FOLDER}
    sys.path.append(os.path.join(build_config.MY_WORKSPACE, project_name, 'tests'))
    sys.path.append(os.path.join(build_config.MY_WORKSPACE, project_name, 'src'))

    given_specs = metafunc.config.getoption('--specs')
    if given_specs:
        generated_specs = []
        for spec_filepath in given_specs:
            with open(spec_filepath, 'r') as spec_json:
                spec_data = json.load(spec_json)
                spec_data.pop('results', None)
                generated_specs.append(spec_data)
    else:
        # collect available tests
        specs_dirpath = os.path.join(build_config.MY_WORKSPACE, project_name,
                                     'tests', 'specs')        

        available_specs = []
        specs_files_paths = Path(specs_dirpath).rglob('*.yaml')
        # general defaults
        with open(os.path.join(os.path.dirname(__file__), 'defaults.yaml'), 'r') as defaults_file:
            defaults = yaml.safe_load(defaults_file)

        # project/build specific defaults use inly if exists
        build_specific_defaults_path = os.path.join(build_config.MY_WORKSPACE, project_name, 'tests', 'specs', 'defaults.yaml')
        if os.path.isfile(build_specific_defaults_path):
            with open(build_specific_defaults_path, 'r') as build_defaults_file:
                defaults.update(yaml.safe_load(build_defaults_file))

        for specs_file_path in specs_files_paths:
            specs_file_path = str(specs_file_path)
            with open(specs_file_path, 'r') as specs_file:
                file_specs = yaml.safe_load(specs_file)
                for file_spec_name, file_spec in file_specs.items():
                    if 'defaults' not in file_spec_name:  # skip defaults specs
                        file_spec['template'] = copy.deepcopy(file_spec)
                        # update name of test
                        file_spec['name'] = file_spec_name
                        file_spec['project'] = project_name

                        # update module of test 
                        file_spec['module'] = specs_file_path.split('specs/')[1][:-5].replace('/', '.')
                        available_specs.append(file_spec)

                        file_spec['artifacts_dir'] = build_config.ARTIFACTS_DIR
                        
                        # add defaults from defaults.yaml

                        def update(d, u):
                            for k, v in u.items():
                                if isinstance(v, collections.abc.Mapping) and k != 'template':
                                    d[k] = update(d.get(k, {}), v)
                                else:
                                    d[k] = v
                            return d

                        #### new update implementation
                        override_spec = copy.deepcopy(file_spec)
                        update(file_spec, defaults)
                        update(file_spec, override_spec)

        # pick selected tests based on the inputs to the tests
        selected_specs = select(metafunc.config, available_specs)

        # genereate from params
        initial_generated_specs = []
        for selected_spec in selected_specs:
            # constant params
            params = selected_spec.get('params')
            if params:  # constant params
                for values in selected_spec['values']:
                    initial_generated_spec = copy.deepcopy(selected_spec)
                    initial_generated_spec['params'] = dict(zip(params, values))

                    # add unique id for the spec - it can be duplicated
                    initial_generated_specs.append(initial_generated_spec)
            else:
                initial_generated_spec = copy.deepcopy(selected_spec)
                initial_generated_spec['params'] = {}
                initial_generated_specs.append(initial_generated_spec)

        # update specs based on generator
        generator_specs = []
        for initial_generated_spec in initial_generated_specs:
            # generator
            generator_str_rep = initial_generated_spec.get('generator')
            if generator_str_rep:  # generator
                params_generator = get_function_instance(project_name, generator_str_rep)
                params_list = params_generator()
                for params in params_list:
                    generator_spec = copy.deepcopy(initial_generated_spec)
                    generator_spec['params'].update(params)
                    generator_specs.append(generator_spec)
            else:
                generator_specs.append(initial_generated_spec)

        # randomized params
        generated_specs = []
        for generator_spec in generator_specs:
            if generator_spec.get('random'):  # randomization
                random_params = generator_spec['random']
                count = random_params.get('count', 1)
                for _ in range(count):
                    generated_spec = copy.deepcopy(generator_spec)
                    distribution_funcs = {
                        'uniform': random.uniform,
                        'normal': random.normalvariate
                    }
                    for var, random_data in random_params['params'].items():
                        min_value = random_data.get('min', 1)
                        max_value = random_data.get('max', 100)
                        dist_type = random_data.get('type', 'uniform')
                        random_func = distribution_funcs[dist_type]
                        value = random_func(min_value, max_value)
                        generated_spec['params'][var] = value

                    generated_specs.append(generated_spec)
            else:
                generated_specs.append(generator_spec)

    if not generated_specs:
        raise Exception('no tests were selected')

    # update each spec with id and unique data
    for generated_spec in generated_specs:
        if not (given_specs and os.getenv('BUILD_NUMBER')):
            generated_spec['id'] = datetime.now().strftime('%d%m%H%M%S') + str(uuid4().hex)
            generated_spec['output_dir'] = os.path.join(build_config.RESULTS_DIR, generated_spec['id'])
        generated_spec['results'] = {}

    # TODO: sort by priorities
    if 'spec' in metafunc.fixturenames:
        metafunc.parametrize('spec', generated_specs)


def pytest_collection_modifyitems(items):
    for item in items:
        if hasattr(item, 'callspec') and 'spec' in item.callspec.params:
            updated_test_name = '_'.join([item.callspec.params['spec']['name'], item.callspec.params['spec']['id']])
            # name we see when we run collection
            item.name = updated_test_name
            # name of test shםwn on screen
            item._nodeid = updated_test_name


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):  # pylint: disable=unused-argument
    """
    execute all other hooks to obtain the report object
    """
    outcome = yield
    report = outcome.get_result()

    # write raw test params data to file
    if report.when == "call":
        if item.name != 'test_using_queue':
            spec = item.funcargs['spec']
            output_dir = spec['output_dir']
            os.makedirs(output_dir, exist_ok=True)

            def convert_to_dict(spec):
                for k, v in spec.items():
                    if isinstance(v, collections.abc.Mapping) and k != 'template':
                        convert_to_dict(spec[k])
                    else:
                        if hasattr(spec[k], 'to_dict'):
                            spec[k] = spec[k].to_dict()
                        elif hasattr(spec[k], '__dict__'):
                            convert_to_dict(spec[k].__dict__)
                            spec[k] = spec[k].__dict__
                return spec
            
            spec['results']['passed'] = report.passed
            # TODO: check exception is written down
            if not report.passed:
                spec['results']['exception'] = str(call.excinfo)

            with open(os.path.join(spec['output_dir'],
                                   'spec.json'), 'w') as spec_json:

                json.dump(spec, spec_json)


def select_tests(pytest_config, available_spec):
    """Retrives selected specs based on given --tests in the cli
    
    Args:
        pytest_config ([type]): ptest config object
        available_specs ([type]): list of available specs from specs/*.yaml files
    
    Returns:
        [bool]: True id spec module is in given cli modules values
    """

    return available_spec['name'] in pytest_config.getoption('--tests')


def select_modules(pytest_config, available_spec):
    """Retrives selected specs based on given --modules in the cli
    
    Args:
        pytest_config ([type]): ptest config object
        available_specs ([type]): list of available specs from specs/*.yaml files
    
    Returns:
        [bool]: True id spec module is in given cli modules values
    """

    return available_spec['module'] in pytest_config.getoption('--modules')


def select_specs(specs_paths):
    """ reproduce a test from spec (override 'results' key)
    """

    selected_specs = []
    for spec_path in specs_paths:
        with open(spec_path ,'r') as spec_json:
            spec = spec_json.load(spec_json)

        selected_specs.append(spec)

    return selected_specs


def select_tags(pytest_config, available_spec):
    """Retrives selected specs based on given --include --exclude tags in the cli
    
    Args:
        pytest_config ([type]): ptest config object
        available_specs ([type]): list of available specs from specs/*.yaml files
    
    Returns:
        [bool]: True id spec has given tag False if has excluded tag or doesn't have the non of included tests
    """

    inclusions = pytest_config.getoption('--include')
    exclusions = pytest_config.getoption('--exclude')

    tags = available_spec.get('tags')
    is_valid_spec = False
    if tags:
        for inclusion in inclusions:
            if inclusion in tags:
                is_valid_spec = True 
                break

        for exclusion in exclusions:
            if exclusion in tags:
                is_valid_spec = False
                break
    else:
        # in case there are no tags for spec include him 
        if not inclusions:
            is_valid_spec = True

    return is_valid_spec


def select(pytest_config, available_specs):
    """Retrives selected specs based on cli args
    
    Args:
        pytest_config ([type]): ptest config object
        available_specs ([type]): list of available specs from specs/*.yaml files
    
    Returns:
        [list]: specs
    """

    selected_specs = []
    selectors = {
        'tests': select_tests,
        'tags': select_tags,
        'modules': select_modules
    }

    selection_method = None
    if pytest_config.getoption('--include') or pytest_config.getoption('--exclude'):
        selection_method = 'tags'
    elif pytest_config.getoption('--modules'):
        selection_method = 'modules'
    elif pytest_config.getoption('--tests'):
        selection_method = 'tests'
    elif  pytest_config.getoption('--specs'):
        selection_method = 'specs'

    if selection_method:
        if selection_method != 'specs':
            selector = selectors[selection_method]
            for available_spec in available_specs:
                if selector(pytest_config, available_spec) and available_spec.get('enabled', True):
                    selected_specs.append(available_spec)
        elif selection_method == 'specs':
            pass
    else:
        selected_specs = available_specs

    return selected_specs
