'''
helper functions for package management
'''

import subprocess
import logging


def ccall(*args, **kwargs):
    '''
    subprocess.check_call wrapper (shorthand)
    '''
    logging.debug('executing %s', args)
    kwargs['universal_newlines'] = True
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.PIPE

    process = subprocess.Popen(*args, **kwargs)
    (stdout, stderr) = process.communicate()

    if stdout:
        logging.debug(stdout)
    if stderr:
        logging.error(stderr)

    if process.returncode != 0:
        raise subprocess.CalledProcessError('%s terminated with non-zero exit code', args)

    return (stdout, stderr, process.returncode)
