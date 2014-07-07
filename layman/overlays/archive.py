#!/usr/bin/python
from __future__ import unicode_literals

import os
import os.path
import sys
import shutil
import tempfile

import xml.etree.ElementTree as ET # Python 2.5

from  layman.compatibility     import fileopen
from  layman.overlays.source   import OverlaySource, require_supported
from  layman.utils             import path
from  layman.version           import VERSION
from  sslfetch.connections     import Connector

USERAGENT = "Layman-" + VERSION

class ArchiveOverlay(OverlaySource):

    type = 'Archive'
    type_key = 'archive'

    def __init__(self, parent, config, _location, ignore = 0):
        
        super(ArchiveOverlay, self).__init__(parent,
            config, _location, ignore)

        self.output = config['output']
        self.proxies = config.proxies
        self.branch = self.parent.branch


    def _extract(self, base, archive_url, dest_dir):
        '''
        Extracts overlay source archive.

        @params base: string of directory base for installed overlays.
        @params archive_url: string of URL where archive is located.
        @params dest_dir: string of destination of extracted archive.
        @rtype bool
        '''
        clean_archive = self.config['clean_archive']
        ext = self.get_extension()
 
        if 'file://' not in archive_url:
            # set up ssl-fetch output map
            connector_output = {
                'info': self.output.debug,
                'error': self.output.error,
                'kwargs-info': {'level': 2},
                'kwargs-error': {'level': None},
            }

            fetcher = Connecter(connector_output, self.proxies, USERAGENT)

            success, archive, timestamp = fetcher.fetch_content(archive_url)

            pkg = path([base, self.parent.name + ext])

            try:
                with fileopen(pkg, 'w+b') as out_file:
                    out_file.write(archive)

            except Exception as error:
                raise Exception('Failed to store archive package in '\
                                '%(pkg)s\nError was: %(error)s'\
                                % ({'pkg': pkg, 'error': error}))
        
        else:
            clean_archive = False
            pkg = archive_url.replace('file://', '')

        result = self.extract(pkg, dest_dir)

        if clean_archive:
            os.unlink(pkg)
        return result


    def _add_unchecked(self, base):
        def try_to_wipe(folder):
            if not os.path.exists(folder):
                return

            try:
                self.output.info('Deleting directory %(dir)s'\
                    % ({'dir': folder}), 2)
                shutil.rmtree(folder)
            except Exception as error:
                raise Exception('Failed to remove unneccessary archive'\
                    'structure %(dir)s\nError was: %(err)s'\
                    % ({'dir': folder, 'err': error}))

        final_path = path([base, self.parent.name])
        temp_path = tempfile.mkdtemp(dir=base)
        try:
            result = self._extract(base=base, archive_url=self.src,
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
                    raise Exception('Failed to rename archive subdirectory'\
                        '%(src)s to %(path)s\nError was: %(err)s'\
                        % ({'src': source, 'path': final_path, 'err': error}))
                os.chmod(final_path, 0o755)
            else:
                raise Exception('The given path (branch setting in the xml)\n'\
                    '%(src)s does not exist in this archive package!'\
                    % ({'src': source}))

        try_to_wipe(temp_path)
        return result


    def add(self, base):
        '''
        Add overlay.

        @params base: string location where overlays are installed.
        @rtype bool
        '''
        
        if not self.supported():
            return 1

        target = path([base, self.parent.name])

        if os.path.exists(target):
            raise Exception('Directory %(dir)s already exists. Will not'\
                'overwrite its contents!' % ({'dir': target}))

        return self.postsync(
            self._add_unchecked(base),
            cwd=target)


    def sync(self, base):
        '''
        Sync overlay.

        @params base: string location where overlays are installed.
        @rtype bool
        '''

        if not self.supported():
            return 1

        target = path([base, self.parent.name])

        return self.postsync(
            self._add_unchecked(base),
            cwd=target)


    def supported(self):
        '''
        Determines if overlay type is supported.

        @rtype bool
        '''

        return self.is_supported()


if __name__ == '__main__':
    import doctest

    # Ignore warnings here. We are just testing.
    from warnings    import filterwarnings, resetwarnings
    filterwarnings('ignore')

    doctest.testmod(sys.modules[__name__])

    resetwarnings()
