import os
import subprocess


def _shell(command, cwd=None):
    """runs command in shell

    Args:
        command (str): will be executed in the shell

    Returns:
        str: standard output string of shell

    Raises:
        Exception: if shell command returned error_code is not 0

    """

    #logger.info(f'Executing: {command}')
    process = subprocess.Popen(command, stderr=subprocess.STDOUT,
                               stdout=subprocess.PIPE, shell=True, cwd=cwd)

    lines = []
    for line in iter(process.stdout.readline, b''):
        line = line.rstrip().decode('utf8')
        #logger.info(line)

        lines.append(line)

    process.communicate()
    output = '\n'.join(lines)
    if process.returncode:
        raise Exception(f'Failed to run command \'{command}\'\nError code:'
                        f'{process.returncode}\nContent: {output}')

    return output
