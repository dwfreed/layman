# Copyright 2014 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

'''Layman plug-in module for portage.
Performs layman sync actions for layman overlays.
'''

import os

from portage.sync.config_checks import CheckSyncConfig


DEFAULT_CLASS = 'Layman'
AVAILABLE_CLASSES = [ 'Layman',  'PyLayman']
options = {'1': 'Layman', '2': 'PyLayman'}


config_class = DEFAULT_CLASS
try:
    test_param = os.environ["TESTIT"]
    if test_param in options:
        config_class = options[test_param]
except KeyError:
    pass


module_spec = {
    'name': 'layman',
    'description': __doc__,
    'provides':{
        'layman-module': {
            'name': 'layman',
            'class': config_class,
            'description': __doc__,
            'functions': ['sync', 'new', 'exists'],
            'func_desc': {
                'sync': 'Performs a layman sync of the specified overlay',
                'new': 'Currently does nothing',
                'exists': 'Returns a boolean of whether the specified dir ' +
                    'exists and is a valid repository',
            },
            'validate_config': CheckSyncConfig,
        },
    }
}
