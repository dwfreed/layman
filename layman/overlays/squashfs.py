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

import sys

from   layman.overlays.archive  import ArchiveOverlay
from   layman.overlays.source   import require_supported

#===============================================================================
#
# Class SquashfsOverlay
#
#-------------------------------------------------------------------------------

class SquashfsOverlay(ArchiveOverlay):
    ''' Handles squashfs overlays.'''

    type = 'Squashfs'
    type_key = 'squashfs'

    def __init__(self, parent, config, _location, ignore=0):

        super(SquashfsOverlay, self).__init__(parent,
            config, _location, ignore)

        self.output = config['output']


    def get_extension(self):
        '''
        Determines squashfs file extension.

        @rtype str
        '''
        ext = ''
        for i in ('.squashfs', '.squash'):
            candidate_ext = i
            if self.src.endswith(candidate_ext):
                ext = candidate_ext
                break

        return ext


    def extract(self, pkg, dest_dir):
        '''
        Extracts squashfs archive.

        @params pkg: string location where squashfs archive is located.
        @params dest_dir: string of destination of extracted archive.
        @rtype bool
        '''
        # unsquashfs -d TARGET -i -f SOURCE
        args = ['-d', dest_dir, '-i', '-f', pkg]
        result = self.run_command(self.command(), args, cmd=self.type)

        return result


    def is_supported(self):
        '''
        Determines if the overlay type is supported.

        @rtype bool
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
