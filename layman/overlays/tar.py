#!/usr/bin/python
# -*- coding: utf-8 -*-
#################################################################################
# LAYMAN TAR OVERLAY HANDLER
#################################################################################
# File:       tar.py
#
#             Handles tar overlays
#
# Copyright:
#             (c) 2005 - 2008 Gunnar Wrobel
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Gunnar Wrobel <wrobel@gentoo.org>
#
''' Tar overlay support.'''

from __future__ import unicode_literals

__version__ = "$Id: tar.py 310 2007-04-09 16:30:40Z wrobel $"

#===============================================================================
#
# Dependencies
#
#-------------------------------------------------------------------------------

import os
import os.path
import sys
import shutil
import tempfile

import xml.etree.ElementTree as ET # Python 2.5

from   layman.compatibility     import fileopen
from   layman.overlays.source   import OverlaySource, require_supported
from   layman.utils             import path
from   layman.version           import VERSION
from   sslfetch.connections     import Connector

USERAGENT = "Layman" + VERSION

#===============================================================================
#
# Class TarOverlay
#
#-------------------------------------------------------------------------------

class TarOverlay(OverlaySource):
    ''' Handles tar overlays.

    >>> from   layman.output import Message
    >>> import xml.etree.ElementTree as ET # Python 2.5
    >>> repo = ET.Element('repo')
    >>> repo_name = ET.Element('name')
    >>> repo_name.text = 'dummy'
    >>> desc = ET.Element('description')
    >>> desc.text = 'Dummy description'
    >>> owner = ET.Element('owner')
    >>> owner_email = ET.Element('email')
    >>> owner_email.text = 'dummy@example.org'
    >>> owner[:] = [owner_email]
    >>> source = ET.Element('source', type='tar')
    >>> here = os.path.dirname(os.path.realpath(__file__))
    >>> source.text = 'file://' + here + '/../tests/testfiles/layman-test.tar.bz2'
    >>> branch = ET.Element('branch')
    >>> branch.text = 'layman-test'
    >>> repo[:] = [repo_name, desc, owner, source, branch]
    >>> from layman.config import BareConfig
    >>> config = BareConfig()
    >>> import tempfile
    >>> testdir = tempfile.mkdtemp(prefix="laymantmp_")
    >>> from layman.overlays.overlay import Overlay
    >>> a = Overlay(config, repo)
    >>> config['output'].set_colorize(False)
    >>> a.add(testdir)
    0
    >>> os.listdir(testdir + '/dummy/')
    ['layman-test']
    >>> sorted(os.listdir(testdir + '/dummy/layman-test/'))
    ['app-admin', 'app-portage']
    >>> shutil.rmtree(testdir)
    '''

    type = 'Tar'
    type_key = 'tar'

    def __init__(self, parent, config, _location, ignore = 0):

        super(TarOverlay, self).__init__(parent,
            config, _location, ignore)

        self.output = config['output']
        self.proxies = config.proxies
        self.branch = self.parent.branch


    def _extract(self, base, tar_url, dest_dir):
        ext = '.tar.noidea'
        clean_tar = self.config['clean_tar']
        for i in [('tar.%s' % e) for e in ('bz2', 'gz', 'lzma', 'xz', 'Z')] \
                + ['tgz', 'tbz', 'taz', 'tlz', 'txz']:
            candidate_ext = '.%s' % i
            if self.src.endswith(candidate_ext):
                ext = candidate_ext
                break

        if 'file://' not in tar_url:
            # setup the ssl-fetch output map
            connector_output = {
                'info':  self.output.debug,
                'error': self.output.error,
                'kwargs-info': {'level': 2},
                'kwargs-error':{'level': None},
            }

            fetcher = Connector(connector_output, self.proxies, USERAGENT)

            success, tar, timestamp = fetcher.fetch_content(tar_url)

            pkg = path([base, self.parent.name + ext])

            try:
                with fileopen(pkg, 'w+b') as out_file:
                    out_file.write(tar)

            except Exception as error:
                raise Exception('Failed to store tar package in '
                                + pkg + '\nError was:' + str(error))
        else:
            clean_tar = False
            pkg = tar_url.replace('file://', '')

        # tar -v -x -f SOURCE -C TARGET
        args = ['-v', '-x', '-f', pkg, '-C', dest_dir]
        result = self.run_command(self.command(), args, cmd=self.type)

        if clean_tar:
            os.unlink(pkg)
        return result

    def _add_unchecked(self, base):
        def try_to_wipe(folder):
            if not os.path.exists(folder):
                return

            try:
                self.output.info('Deleting directory "%s"' % folder, 2)
                shutil.rmtree(folder)
            except Exception as error:
                raise Exception('Failed to remove unnecessary tar structure "'
                                + folder + '"\nError was:' + str(error))

        final_path = path([base, self.parent.name])
        temp_path = tempfile.mkdtemp(dir=base)
        try:
            result = self._extract(base=base, tar_url=self.src,
                dest_dir=temp_path)
        except Exception as error:
            try_to_wipe(temp_path)
            raise error

        if result == 0:
            if self.branch:
                source = temp_path + '/' + self.branch
            else:
                source = temp_path

            if os.path.exists(source):
                if os.path.exists(final_path):
                    self.delete(base)

                try:
                    os.rename(source, final_path)
                except Exception as error:
                    raise Exception('Failed to rename tar subdirectory ' +
                                    source + ' to ' + final_path +
                                    '\nError was:' + str(error))
                os.chmod(final_path, 0o755)
            else:
                raise Exception('The given path (branch setting in the xml)\n' + \
                    '"%(source)s" does not exist in the tar package!' % ({'source': source}))

        try_to_wipe(temp_path)
        return result

    def add(self, base):
        '''Add overlay.'''

        if not self.supported():
            return 1

        target = path([base, self.parent.name])

        if os.path.exists(target):
            raise Exception('Directory ' + target + ' already exists.' +\
                ' Will not overwrite its contents!')

        return self.postsync(
            self._add_unchecked(base),
            cwd=target)

    def sync(self, base):
        '''Sync overlay.'''

        if not self.supported():
            return 1

        target = path([base, self.parent.name])

        return self.postsync(
            self._add_unchecked(base),
            cwd=target)

    def supported(self):
        '''Overlay type supported?'''

        return require_supported(
            [(self.command(),  'tar', 'app-arch/tar'), ],
            self.output.warn)

if __name__ == '__main__':
    import doctest

    # Ignore warnings here. We are just testing
    from warnings     import filterwarnings, resetwarnings
    filterwarnings('ignore')

    doctest.testmod(sys.modules[__name__])

    resetwarnings()
