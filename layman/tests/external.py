# -*- coding: utf-8 -*-
#################################################################################
# EXTENRAL LAYMAN TESTS
#################################################################################
# File:       external.py
#
#             Runs external (non-doctest) test cases.
#
# Copyright:
#             (c) 2009        Sebastian Pipping
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Sebastian Pipping <sebastian@pipping.org>
#

from __future__ import print_function

'''Runs external (non-doctest) test cases.'''

import os
import sys
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET # Python 2.5
#Py3
try:
    import urllib.request as urllib
except ImportError:
    import urllib

from  layman.argsparser       import ArgsParser
from  layman.api              import LaymanAPI
from  layman.db               import DB
from  layman.dbbase           import DbBase
from  layman.compatibility    import fileopen
from  layman.config           import BareConfig, OptionConfig
from  layman.maker            import Interactive
from  layman.output           import Message
from  layman.overlays.overlay import Overlay
from  layman.remotedb         import RemoteDB
from  layman.repoconfmanager  import RepoConfManager
from  layman.utils            import path
from  warnings import filterwarnings, resetwarnings

HERE = os.path.dirname(os.path.realpath(__file__))

class AddDeleteEnableDisableFromDB(unittest.TestCase):

    def test(self):
        tmpdir = tempfile.mkdtemp(prefix='laymantmp_')
        makeconf = os.path.join(tmpdir, 'make.conf')
        reposconf = os.path.join(tmpdir, 'repos.conf')

        make_txt =\
        'PORTDIR_OVERLAY="\n'\
        '$PORTDIR_OVERLAY"'

        # Create the .conf files so layman doesn't
        # complain.
        with fileopen(makeconf, 'w') as f:
            f.write(make_txt)

        with fileopen(reposconf, 'w') as f:
            f.write('')

        my_opts = {
                   'installed' :
                   HERE + '/testfiles/global-overlays.xml',
                   'make_conf' : makeconf,
                   'nocheck'    : 'yes',
                   'storage'   : tmpdir,
                   'repos_conf' : reposconf,
                   'conf_type' : ['make.conf', 'repos.conf'],
                   }

        config = OptionConfig(my_opts)
        config.set_option('quietness', 3)

        a = DB(config)
        config['output'].set_colorize(False)

        conf = RepoConfManager(config, a.overlays)

        # Set up our success tracker.
        success = []

        # Add all the overlays in global_overlays.xml.
        for overlay in a.overlays.keys():
            conf_success = conf.add(a.overlays[overlay])
            if False in conf_success:
                success.append(False)
            else:
                success.append(True)

        # Disable one overlay.
        conf_success = conf.disable(a.overlays['wrobel'])
        if False in conf_success:
            success.append(False)
        else:
            success.append(True)

        # Enable disabled overlay.
        conf_success = conf.enable(a.overlays['wrobel'])
        if False in conf_success:
            success.append(False)
        else:
            success.append(True)
        # Delete all the overlays in global_overlays.xml.
        for overlay in a.overlays.keys():
            conf_success = conf.delete(a.overlays[overlay])
            if False in conf_success:
                success.append(False)
            else:
                success.append(True)

        # Clean up.
        os.unlink(makeconf)
        os.unlink(reposconf)

        shutil.rmtree(tmpdir)

        if False in success:
            success = False
        else:
            success = True

        self.assertTrue(success)


class CLIArgs(unittest.TestCase):

    def test(self):
        # Append cli args to sys.argv with correspoding options:
        sys.argv.append('--config')
        sys.argv.append(HERE + '/../../etc/layman.cfg')

        sys.argv.append('--overlay_defs')
        sys.argv.append('')

        # Test the passed in cli opts on the ArgsParser class:
        a = ArgsParser()

        self.assertTrue(a['overlays'])
        self.assertTrue(sorted(a.keys()))


class CreateConfig(unittest.TestCase):

    def make_BareConfig(self):
        a = BareConfig()

        # Test components of the BareConfig class:
        assertTrue(a['overlay'])
        assertTrue(sorted(a.keys()))
        assertTrue(a.get_option('nocheck'))


    def make_OptionConfig(self):
        my_opts = {
                   'overlays':
                   ["http://www.gentoo-overlays.org/repositories.xml"]
                  }
        new_defaults = {'configdir': '/etc/test-dir'}

        a = OptionConfig(options=my_opts, defaults=new_defaults)

        # Test components of the OptionConfig class:
        assertTrue(a['overlays'])
        assertTrue(a['configdir'])
        assertTrue(sorted(a.keys()))


    def test(self):
        for i in ['BareConfig', 'OptionConfig']:
            getattr(self, 'make_%s' % i)


class FetchRemoteList(unittest.TestCase):

    def test(self):
        tmpdir = tempfile.mkdtemp(prefix='laymantmp_')
        cache = os.path.join(tmpdir, 'cache')

        my_opts = {
                   'overlays': ['file://'\
                                + HERE + '/testfiles/global-overlays.xml'],
                   'cache': cache,
                   'nocheck': 'yes',
                   'proxy': None,
                   'quietness': 3
                  }

        config = OptionConfig(my_opts)

        api = LaymanAPI(config)
        success = api.fetch_remote_list()
        self.assertTrue(success)

        filename = api._get_remote_db().filepath(config['overlays']) + '.xml'

        with fileopen(filename, 'r') as b:
            for line in b.readlines():
                # Test to see if every line
                # is valid.
                self.assertTrue(line)
                print(line, end='')

        # Check if we get available overlays.
        available = api.get_available()
        self.assertTrue(available)

        # Test the info of an overlay.
        all_info = api.get_all_info('wrobel')
        info = all_info['wrobel']
        self.assertTrue(info)

        self.assertTrue(info['status'])
        self.assertTrue(info['description'])
        self.assertTrue(info['sources'])

        os.unlink(filename)
        shutil.rmtree(tmpdir)


class FormatBranchCategory(unittest.TestCase):
    def _run(self, number):
        #config = {'output': Message()}
        config = BareConfig()
        # Discuss renaming files to "branch-%d.xml"
        filename1 = os.path.join(HERE, 'testfiles',
                'subpath-%d.xml' % number)

        # Read, write, re-read, compare
        os1 = DbBase(config, [filename1])
        filename2 = tempfile.mkstemp()[1]
        os1.write(filename2)
        os2 = DbBase(config, [filename2])
        os.unlink(filename2)
        self.assertTrue(os1 == os2)

        # Pass original overlays
        return os1

    def test(self):
        os1 = self._run(1)
        os2 = self._run(2)

        # Same content from old/layman-global.txt
        #   and new/repositories.xml format?
        self.assertTrue(os1 == os2)


class MakeOverlayXML(unittest.TestCase):

    def test(self):
        temp_dir_path = tempfile.mkdtemp()
        my_opts = {
                   'overlays': ['file://'\
                        + HERE + '/testfiles/global-overlays.xml'],
                   'nocheck': 'yes',
                   'proxy': None,
                   'quietness': 3,
                  }

        config = OptionConfig(my_opts)

        ovl_dict = {
                    'name': 'wrobel',
                    'descriptions': ['Test'],
                    'owner_name': 'nobody',
                    'owner_email': 'nobody@gentoo.org',
                    'status': 'official',
                    'sources': [['https://overlays.gentoo.org/svn/dev/wrobel',
                                 'svn', '']],
                    'priority': '10',
                   }

        a = Overlay(config=config, ovl_dict=ovl_dict, ignore=config['ignore'])
        ovl = (ovl_dict['name'], a)
        path = temp_dir_path + '/overlay.xml'
        create_overlay_xml = Interactive()

        create_overlay_xml(overlay_package=ovl, path=path)
        self.assertTrue(os.path.exists(path))

        with fileopen(path, 'r') as xml:
            for line in xml.readlines():
                self.assertTrue(line)
                print(line, end='')

        shutil.rmtree(temp_dir_path)


class OverlayObjTest(unittest.TestCase):

    def objattribs(self):
        document = ET.parse(HERE + '/testfiles/global-overlays.xml')
        overlays = document.findall('overlay') + document.findall('repo')
        output = Message()

        ovl_a = Overlay({'output': output}, overlays[0])
        self.assertEqual(ovl_a.name, 'wrobel')
        self.assertEqual(ovl_a.is_official(), True)
        self.assertEqual(\
            list(ovl_a.source_uris()),
            ['https://overlays.gentoo.org/svn/dev/wrobel'])
        self.assertEqual(ovl_a.owner_email, 'nobody@gentoo.org')
        self.assertEqual(ovl_a.descriptions, ['Test'])
        self.assertEqual(ovl_a.priority, 10)

        ovl_b = Overlay({'output': output}, overlays[1])
        self.assertEqual(ovl_b.is_official(), False)


    def getinfostr(self):
        document = ET.parse(HERE + '/testfiles/global-overlays.xml')
        overlays = document.findall('overlay') + document.findall('repo')
        output = Message()

        ovl = Overlay({'output': output}, overlays[0])
        print(ovl.get_infostr())


    def getshortlist(self):
        document = ET.parse(HERE + '/testfiles/global-overlays.xml')
        overlays = document.findall('overlay') + document.findall('repo')
        output = Message()

        ovl = Overlay({'output': output}, overlays[0])
        print(ovl.short_list(80))


    def test(self):
        self.objattribs()
        self.getinfostr()
        self.getshortlist()


class PathUtil(unittest.TestCase):

    def test(self):
        self.assertEqual(path([]), '')
        self.assertEqual(path(['a']), 'a')
        self.assertEqual(path(['a', 'b']), 'a/b')
        self.assertEqual(path(['a/', 'b']), 'a/b')
        self.assertEqual(path(['/a/', 'b']), '/a/b')
        self.assertEqual(path(['/a', '/b/']), '/a/b')
        self.assertEqual(path(['/a/', 'b/']), '/a/b')
        self.assertEqual(path(['/a/','/b/']), '/a/b')
        self.assertEqual(path(['/a/','/b','c/']), '/a/b/c')


class Unicode(unittest.TestCase):
    def _overlays_bug(self, number):
        config = BareConfig()
        filename = os.path.join(HERE, 'testfiles', 'overlays_bug_%d.xml'\
                                                    % number)
        o = DbBase(config, [filename])
        for verbose in (True, False):
            for t in o.list(verbose=verbose):
                print(t[0].decode('utf-8'))
                print()

    def test_184449(self):
        self._overlays_bug(184449)

    def test_286290(self):
        self._overlays_bug(286290)


class ReadWriteSelectListDbBase(unittest.TestCase):

    def list_db(self):
        output = Message()
        config = {
                  'output': output,
                  'svn_command': '/usr/bin/svn',
                  'rsync_command':'/usr/bin/rsync'
                 }
        db = DbBase(config, [HERE + '/testfiles/global-overlays.xml', ])

        for info in db.list(verbose=True):
            self.assertTrue(info[0])
            print(info[0])

        for info in db.list(verbose=False, width=80):
            self.assertTrue(info[0])
            print(info[0])


    def read_db(self):
        output = Message()
        config = {'output': output}
        db = DbBase(config, [HERE + '/testfiles/global-overlays.xml', ])
        self.assertEqual(db.overlays.keys(), ['wrobel', 'wrobel-stable'])

        self.assertEqual(\
            list(db.overlays['wrobel-stable'].source_uris()),
            ['rsync://gunnarwrobel.de/wrobel-stable'])


    def select_db(self):
        output = Message()
        config = {'output': output}
        db = DbBase(config, [HERE + '/testfiles/global-overlays.xml', ])
        self.assertEqual(\
            list(db.select('wrobel-stable').source_uris()),
            ['rsync://gunnarwrobel.de/wrobel-stable'])


    def write_db(self):
        tmpdir = tempfile.mkdtemp(prefix='laymantmp_')
        test_xml = os.path.join(tmpdir, 'test.xml')
        config = BareConfig()
        a = DbBase(config, [HERE + '/testfiles/global-overlays.xml', ])
        b = DbBase({'output': Message()}, [test_xml,])

        b.overlays['wrobel-stable'] = a.overlays['wrobel-stable']
        b.write(test_xml)

        c = DbBase({'output': Message()}, [test_xml,])
        self.assertEquals(c.overlays.keys(), ['wrobel-stable'])

        # Clean up:
        os.unlink(test_xml)
        shutil.rmtree(tmpdir)


    def test(self):
        self.list_db()
        self.read_db()
        self.select_db()
        self.write_db()


class RemoteDBCache(unittest.TestCase):
    def test(self):
        tmpdir = tempfile.mkdtemp(prefix='laymantmp_')
        cache = os.path.join(tmpdir, 'cache')
        my_opts = {
                   'overlays' :
                   ['file://' + HERE + '/testfiles/global-overlays.xml'],
                   'cache' : cache,
                   'nocheck'    : 'yes',
                   'proxy' : None
                  }
        config = OptionConfig(my_opts)
        db = RemoteDB(config)
        self.assertEquals(db.cache(), (True, True))

        db_xml = fileopen(db.filepath(config['overlays']) + '.xml')

        for line in db_xml.readlines():
            self.assertTrue(line)
            print(line, end='')

        db_xml.close()
        self.assertEqual(db.overlays.keys(), ['wrobel', 'wrobel-stable'])

        shutil.rmtree(tmpdir)


# http://bugs.gentoo.org/show_bug.cgi?id=304547
class TarAddRemoveSync(unittest.TestCase):
    def test(self):
        repo_name = 'tar-test-overlay'
        tar_source_path = os.path.join(HERE, 'testfiles', 'layman-test.tar.bz2')

        # Duplicate test tarball (so we have it deletable for later)
        (_, temp_tarball_path) = tempfile.mkstemp()
        shutil.copyfile(tar_source_path, temp_tarball_path)

        # Write overlay collection XML
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<repositories xmlns="" version="1.0">
  <repo quality="experimental" status="unofficial">
    <name>%(repo_name)s</name>
    <description>XXXXXXXXXXX</description>
    <owner>
      <email>foo@exmaple.org</email>
    </owner>
    <source type="tar">file://%(temp_tarball_url)s</source>
  </repo>
</repositories>
""" % {     'temp_tarball_url':urllib.pathname2url(temp_tarball_path),
            'repo_name':repo_name}
        (fd, temp_collection_path) = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(xml_text)

        # Make playground directory
        temp_dir_path = tempfile.mkdtemp()

        # Make DB from it
        #config = {'output': Message(), 'tar_command':'/bin/tar'}
        config = BareConfig()
        db = DbBase(config, [temp_collection_path])

        specific_overlay_path = os.path.join(temp_dir_path, repo_name)
        o = db.select('tar-test-overlay')

        # Actual testcase
        o.add(temp_dir_path)
        self.assertTrue(os.path.exists(specific_overlay_path))
        # (1/2) Sync with source available
        o.sync(temp_dir_path)
        self.assertTrue(os.path.exists(specific_overlay_path))
        os.unlink(temp_tarball_path)
        try:
            # (2/2) Sync with source _not_ available
            o.sync(temp_dir_path)
        except:
            pass
        self.assertTrue(os.path.exists(specific_overlay_path))
        o.delete(temp_dir_path)
        self.assertFalse(os.path.exists(specific_overlay_path))

        # Cleanup
        os.unlink(temp_collection_path)
        os.rmdir(temp_dir_path)


if __name__ == '__main__':
    filterwarnings('ignore')
    unittest.main()
    resetwarnings()
