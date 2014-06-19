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


    def _get_optargs(self, args):
         if self.settings:
            if self.settings.get('NOCOLOR'):
                args.append('-N')
            if self.settings.get('PORTAGE_QUIET'):
                args.append('-q')

    def new(self, **kwargs):
        '''Use layman to install the repository'''
        if kwargs:
            self._kwargs(kwargs)
        emerge_config = self.options.get('emerge_config', None)
        portdb = self.options.get('portdb', None)
        args = []
        msg = '>>> Starting to add new layman overlay %(repo)s' % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')

        args.append('layman -n')
        self._get_optargs(args)
        args.append('-a')
        args.append(self.repo.name)

        command = ' '.join(args)

        exitcode = portage.process.spawn_bash("%(command)s" % \
            ({'command': command}),
            **portage._native_kwargs(self.spawn_kwargs))
        if exitcode != os.EX_OK:
            msg = "!!! layman add error in %(repo)s" % ({'repo': self.repo.name})
            self.logger(self.xterm_titles, msg)
            writemsg_level(msg + "\n", level=logging.ERROR, noiselevel=-1)
            return (exitcode, False)
        msg = ">>> Addition of layman repo succeeded: %(repo)s" % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + "\n")

        return (exitcode, True)

    def _sync(self):
        ''' Update existing repository'''
        emerge_config = self.options.get('emerge_config', None)
        portdb = self.options.get('portdb', None)
        args = []
        msg = '>>> Starting layman sync for %(repo)s...' % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')

        args.append('layman -n')
        self._get_optargs(args)
        args.append('-s')
        args.append(self.repo.name)

        command = ' '.join(args)
        exitcode = portage.process.spawn_bash("%(command)s" % \
            ({'command': command}),
            **portage._native_kwargs(self.spawn_kwargs))
        if exitcode != os.EX_OK:
            msg = "!!! layman sync error in %(repo)s" % ({'repo': self.repo.name})
            self.logger(self.xterm_titles, msg)
            writemsg_level(msg + "\n", level=logging.ERROR, noiselevel=-1)
            return (exitcode, False)
        msg = ">>> layman sync succeeded: %(repo)s" % ({'repo': self.repo.name})
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
        SyncBase.__init__(self, 'layman', 'app-portage/layman')

        self._layman = None


    def _get_layman_api(self):

        # Make it so that we aren't initializing the
        # LaymanAPI instance if it already exists.
        if self._layman:
            return self._layman

        config = BareConfig()
        self.message = Message(out=sys.stdout, err=sys.stderr)

        options = {
            'config': config.get_option('config'),
            'quiet': self.settings.get('PORTAGE_QUIET'),
            'quietness': config.get_option('quietness'),
            'output': self.message,
            'nocolor': self.settings.get('NOCOLOR'),
            'root': self.settings.get('EROOT'),
            'verbose': self.settings.get('PORTAGE_VERBOSE'),
            'width': self.settings.get('COLUMNWIDTH'),

        }

        self.config = OptionConfig(options=options)

        layman_api = LaymanAPI(self.config,
                               report_errors=True,
                               output=self.config['output']
                               )

        self._layman = layman_api

        return layman_api

    def new(self, **kwargs):
        '''Do the initial download and install of the repository'''
        layman_inst = self._get_layman_api()

        emerge_config = self.options.get('emerge_config', None)
        portdb = self.options.get('portdb', None)

        msg = '>>> Starting to add new layman overlay %(repo)s' % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')

        exitcode = layman_inst.add_repos(self.repo.name)
        if exitcode != os.EX_OK:
            msg = "!!! layman add error in %(repo)s" % ({'repo': self.repo.name})
            self.logger(self.xterm_titles, msg)
            writemsg_level(msg + "\n", level=logging.ERROR, noiselevel=-1)
            return (exitcode, False)
        msg = ">>> Addition of layman repo succeeded: %(repo)s" % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')
   
    def _sync(self):
        ''' Update existing repository'''
        layman_inst = self._get_layman_api()

        emerge_config = self.options.get('emerge_config', None)
        portdb = self.options.get('portdb', None)

        msg = '>>> Starting layman sync for %(repo)s...' % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + '\n')

        exitcode = layman_inst.sync(self.repo.name)
        if exitcode != os.EX_OK:
            msg = "!!! layman sync error in %(repo)s" % ({'repo': self.repo.name})
            self.logger(self.xterm_titles, msg)
            writemsg_level(msg + "\n", level=logging.ERROR, noiselevel=-1)
            return (exitcode, False)
        msg = ">>> layman sync succeeded: %(repo)s" % ({'repo': self.repo.name})
        self.logger(self.xterm_titles, msg)
        writemsg_level(msg + "\n")

        return(exitcode, True)
