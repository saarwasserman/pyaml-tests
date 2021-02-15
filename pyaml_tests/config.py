import os


BUILD_ID = os.getenv('CI_BUILD_ID')  # from ci tool
BUILD_NAME = os.getenv('CI_PROJECT_NAME')  # from project dir


class BaseConfig():

    AUTOMATION_DIR = '/automation'
    MY_WORKSPACE = os.getenv('MY_WORKSPACE') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DevConfig(BaseConfig):
    RESULTS_DIR = f'/tmp/results'
    ARTIFACTS_DIR = '/tmp/artifacts'


class StagingConfig(BaseConfig):
    pass

class ProductionConfig(BaseConfig):
    RESULTS_DIR = f'/automation/results/{BUILD_NAME}/{BUILD_ID}'
    ARTIFACTS_DIR = '/automation/artifacts'


def get_config(pytest_config):

    if os.getenv('PRODUCTION'):
        env_type = 'production'
    elif os.getenv('STAGING'):
        env_type = 'staging'
    else:
        env_type = 'dev'

    envs = {
        'dev': DevConfig(),
        'staging': StagingConfig(),
        'production': ProductionConfig()
    }

    config = envs[env_type]

    # dev environment adjustments
    build_dir = pytest_config.getoption('--build_dir')
    if build_dir:  # for dev use
        config.ARTIFACTS_DIR = os.path.join(build_dir, 'artifacts')
        config.RESULTS_DIR = os.path.join(build_dir, 'results')

    if env_type == 'dev':
        project_name = pytest_config.getoption('--project')
        config.RESULTS_DIR = os.path.join(config.RESULTS_DIR, project_name)

    return config
