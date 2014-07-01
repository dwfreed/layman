#!/usr/bin/python
# -*- coding: utf-8 -*-
#################################################################################
# LAYMAN SQUASHFS OVERLAY HANDLER
#################################################################################
# File:       squashfs.py
#
#             Handles squashfs overlays
#
# Copyright:
#             (c) 2014 Devan Franchini
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Devan Franchini <twitch153@gentoo.org>
#
''' Squashfs overlay support.'''

from __future__ import unicode_literals

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

class SquashfsOverlay(OverlaySource):
    ''' Handles squashfs overlays.'''

    type = 'Squashfs'
    type_key = 'squashfs'

    def __init__(self, parent, config, _location, ignore = 0):

        super(SquashfsOverlay, self).__init__(parent,
            config, _location, ignore)

        self.output = config['output']
        self.proxies = config.proxies
        self.branch = self.parent.branch


    def _extract(self, base, squashfs_url, dest_dir):
        '''
        Extracts squashfs archive.

        @params base: string of directory base for installed overlays.
        @params squashfs_url: string of URL archive is located.
        @params dest_dir: string of destination of extracted archive.
        @rtype boolean
        '''
        clean_squashfs = self.config['clean_archive']

        if 'file://' not in squashfs_url:
            # setup the ssl-fetch output map
            connector_output = {
                'info':  self.output.debug,
                'error': self.output.error,
                'kwargs-info': {'level': 2},
                'kwargs-error':{'level': None},
            }

            fetcher = Connector(connector_output, self.proxies, USERAGENT)

            success, squashfs, timestamp = fetcher.fetch_content(squashfs_url)

            pkg = path([base, self.parent.name])

            try:
                with fileopen(pkg, 'w+b') as out_file:
                    out_file.write(squashfs)

            except Exception as error:
                raise Exception('Failed to store squashfs package in '
                                + pkg + '\nError was:' + str(error))
        else:
            clean_squashfs = False
            pkg = squashfs_url.replace('file://', '')

        # unsquashfs -d TARGET -i -f SOURCE
        args = ['-d', dest_dir, '-i', '-f', pkg]
        result = self.run_command(self.command(), args, cmd=self.type)

        if clean_squashfs:
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
                raise Exception('Failed to remove unnecessary squashfs structure "'
                                + folder + '"\nError was:' + str(error))

        final_path = path([base, self.parent.name])
        temp_path = tempfile.mkdtemp(dir=base)
        try:
            result = self._extract(base=base, squashfs_url=self.src,
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
                    raise Exception('Failed to rename squashfs subdirectory ' +
                                    source + ' to ' + final_path +
                                    '\nError was:' + str(error))
                os.chmod(final_path, 0o755)
            else:
                raise Exception('The given path (branch setting in the xml)\n' + \
                    '"%(source)s" does not exist in the squashfs package!' % ({'source': source}))

        try_to_wipe(temp_path)
        return result

    def add(self, base):
        '''
        Add overlay.

        @params base: string location where overlays are installed.
        @rtype boolean
        '''

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
        '''
        Sync overlay.

        @params base: string location where overlays are installed
        @rtype boolean
        '''

        if not self.supported():
            return 1

        target = path([base, self.parent.name])

        return self.postsync(
            self._add_unchecked(base),
            cwd=target)

    def supported(self):
        '''
        Overlay type supported?

        @rtype boolean
        '''

        return require_supported(
            [(self.command(),  'squashfs', 'sys-fs/squashfs-tools'), ],
            self.output.warn)

if __name__ == '__main__':
    import doctest

    # Ignore warnings here. We are just testing
    from warnings     import filterwarnings, resetwarnings
    filterwarnings('ignore')

    doctest.testmod(sys.modules[__name__])

    resetwarnings()
