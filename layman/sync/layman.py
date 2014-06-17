# Copyright 2014 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
'''Layman module for portage'''

import logging

from layman.api import LaymanAPI
from layman.config import BareConfig, OptionConfig
from layman.output import Message

import portage
from portage import os
from portage.util import writemsg_level
from portage.output import create_color_func
good = create_color_func("GOOD")
bad = create_color_func("BAD")
warn = create_color_func("WARN")
from portage.sync.syncbase import SyncBase

import sys

class Layman(SyncBase):
    '''Layman sync class'''

    short_desc = "Perform sync operations on webrsync based repositories"

    @staticmethod
    def name():
        return "Layman"


    def __init__(self):
        SyncBase.__init__(self, 'layman', 'app-portage/layman')


    def new(self, **kwargs):
        '''Do the initial download and install of the repository'''
        pass


    def _sync(self):
        ''' Update existing repository'''
        emerge_config = self.options.get('emerge_config', None)
        portdb = self.options.get('portdb', None)
        args = []
        msg = '>>> Starting layman sync for %s...' % self.repo.location
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')
        args.append('layman -n')

        if self.settings:
            if self.settings.get('NOCOLOR'):
                args.append('-N')
            if self.settings.get('PORTAGE_QUIET'):
                args.append('-q')

        args.append('-s')
        args.append(self.repo.name)
        exitcode = portage.process.spawn_bash("%s" % \
            (' '.join(args)),
            **portage._native_kwargs(self.spawn_kwargs))
        if exitcode != os.EX_OK:
            msg = "!!! layman sync error in %s" % self.repo.name
            self.logger(self.xterm_titles, msg)
            writemsg_level(msg + "\n", level=logging.ERROR, noiselevel=-1)
            return (exitcode, False)
        msg = ">>> layman sync succeeded: %s" % self.repo.name
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + "\n")

        return (exitcode, True)


class PyLayman(SyncBase):
    '''Layman sync class'''

    short_desc = "Perform sync operations on webrsync based repositories"

    @staticmethod
    def name():
        return "Layman"

    def __init__(self):

        SyncBase.__init__(self, '', 'app-portage/layman')

        config = BareConfig()
        self.message = Message(out=sys.stdout, err=sys.stderr)
        
        options = {
            'config': config.get_option('config'),
            'quiet': portage.settings.get('PORTAGE_QUIET'),
            'quietness': config.get_option('quietness'),
            'output': self.message,
            'nocolor': portage.settings.get('NOCOLOR'),
            'root': portage.settings.get('EROOT'),
            'verbose': portage.settings.get('PORTAGE_VERBOSE'),
            'width': portage.settings.get('COLUMNWIDTH'),

        }

        self.config = OptionConfig(options=options)
        
        LaymanAPI.__init__(self, self.config,
                             report_errors=True,
                             output=self.config['output']
                            )

    def new(self, **kwargs):
        '''Do the initial download and install of the repository'''
        pass

   
    def _sync(self):
        ''' Update existing repository'''
        pass
