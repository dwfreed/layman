#!/usr/bin/python
# -*- coding: utf-8 -*-
# File:       maker.py
#
#             Creates overlay definitions and writes them to an XML file
#
# Copyright:
#             (c) 2014 Devan Franchini
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Devan Franchini <twitch153@gentoo.org>
#

#===============================================================================              
#
# Dependencies
#                                                   
#-------------------------------------------------------------------------------
from __future__ import unicode_literals

import layman.overlays.overlay as Overlay
import xml.etree.ElementTree   as ET

import copy
import os
import re
import sys

from   layman.api            import LaymanAPI
from   layman.compatibility  import fileopen
from   layman.constants      import COMPONENT_DEFAULTS, POSSIBLE_COMPONENTS
from   layman.config         import OptionConfig
from   layman.utils          import indent, reload_config

#py3
if sys.hexversion >= 0x30200f0:
    _UNICODE = 'unicode'
else:
    _UNICODE = 'UTF-8'

class Interactive(object):

    def __init__(self):
        self.config = OptionConfig()
        reload_config(self.config)
        self.layman_inst = LaymanAPI(config=self.config)
        self.overlay = {}
        self.overlays = []
        self.overlays_available = self.layman_inst.get_available()
        self.supported_types = self.layman_inst.supported_types().keys()

    def __call__(self, overlay_package=None, path=None):

        if not overlay_package:
            for x in range(1, int(self.get_input("How many overlays would you like to create?: "))+1):
                self.info_available = False
                print('')
                print('Overlay #%(x)s: ' % ({'x': str(x)}))
                print('~~~~~~~~~~~~~')

                self.info_available = self.get_ans('Is the mirror for this '\
                    'overlay either github.com or\ngit.overlays.gentoo.org?'\
                    ' [y/n]: ')
                print('')
                self.update_required()
                print('')
                self.get_overlay_components()
                ovl = Overlay.Overlay(config=self.config, ovl_dict=self.overlay, ignore=1)
                self.overlays.append((self.overlay['name'], ovl))
        else:
            ovl_name, ovl = overlay_package
            self.overlays.append((ovl_name, ovl))

        result = self.write(path)
        return result


    def get_input(self, msg):
        '''
        py2 py3 compatibility function
        to obtain user input.

        @params msg: message prompt for user
        @rtype str: input from user
        '''
        try:
            value = raw_input(msg)
        except NameError:
            value = input(msg)
        
        return value


    def get_ans(self, msg):
        '''
        Handles yes/no input

        @params msg: message prompt for user
        @rtype boolean: reflects whether the user answered yes or no.
        '''
        ans = self.get_input(msg).lower()

        while ans not in ('y', 'yes', 'n', 'no'):
            ans = self.get_input('Please respond with [y/n]: ').lower()

        return ans in ('y', 'yes')


    def check_overlay_type(self, ovl_type):
        '''
        Validates overlay type.

        @params ovl_type: str of overlay type
        @rtype None or str (if overlay type is valid).
        '''
        if ovl_type.lower() in self.supported_types:
            return ovl_type.lower()
        print('Specified type "%(type)s" not valid.' % ({'type': ovl_type}))
        print('Supported types include: %(types)s.'\
            % ({'types': ', '.join(self.supported_types)}))
        return None


    def guess_overlay_type(self, source_uri):
        '''
        Guesses the overlay type based on the source given.

        @params source-uri: str of source.
        @rtype None or str (if overlay type was guessed correctly).
        '''

        type_checks = copy.deepcopy(self.supported_types)

        #Modify the type checks for special overlay types.
        if 'tar' in type_checks:
            type_checks.remove(type_checks[type_checks.index('tar')])
            type_checks.insert(len(type_checks), '.tar')
                
        if 'bzr' in type_checks:
            type_checks.remove(self.supported_types[type_checks.index('bzr')])
            type_checks.insert(len(type_checks), 'bazaar')

        for guess in type_checks:
            if guess in source_uri:
                return guess

        if 'bitbucket.org' in source_uri:
            return 'mercurial'

        return None


    def update_required(self):
        '''
        Prompts user for optional components and updates
        the required components accordingly.
        '''
        # Don't assume they want the same
        # info for the next overlay.
        self.required = copy.deepcopy(COMPONENT_DEFAULTS)

        for possible in POSSIBLE_COMPONENTS:
            if possible not in self.required:
                msg = 'Include %(comp)s for this overlay? [y/n]: '\
                        % ({'comp': possible})
                if ((possible in 'homepage' or possible in 'feeds') and
                   self.info_available):
                    available = False
                else:
                    available = self.get_ans(msg)
                if available:
                    self.required.append(possible)


    def get_descriptions(self):
        '''
        Prompts user for an overlay's description(s)
        and updates overlay dict with value(s).
        '''
        #TODO: Currently a "stub" function. Add multiple description
        # field support later down the road.
        descriptions = []

        desc = self.get_input('Define overlay\'s description: ')
        descriptions.append(desc)

        self.overlay['descriptions'] = descriptions


    def get_feeds(self):
        '''
        Prompts user for any overlay RSS feeds
        and updates overlay dict with values.
        '''
        feed_amount = int(self.get_input('How many RSS feeds exist for this overlay?: '))
        feeds = []

        for i in range(1, feed_amount + 1):
            if feed_amount > 1:
                feeds.append(self.get_input('Define overlay feed[%(i)s]: '\
                    % ({'i': str(i)})))
            else:
                feeds.append(self.get_input('Define overlay feed: '))

        self.overlay['feeds'] = feeds
        print('')


    def get_name(self):
        '''
        Prompts user for the overlay name
        and updates the overlay dict.
        '''
        name = self.get_input('Define overlay name: ')

        while name in self.overlays_available:
            print('!!! Overlay name already defined in list of installed overlays.')
            name = self.get_input('Please specify a different overlay name: ')

        self.overlay['name'] = name


    def get_sources(self):
        '''
        Prompts user for possible overlay source
        information such as type, url, and branch
        and then appends the values to the overlay
        being created.
        '''
        ovl_type = None

        if self.info_available:
            source_amount = 1
        else:
            source_amount = int(self.get_input('How many different sources,'\
                    ' protocols, or mirrors exist for this overlay?: '))

        self.overlay['sources'] = []

        for i in range(1, source_amount + 1):
            sources = []
            if source_amount > 1:
                sources.append(self.get_input('Define source[%(i)s] URL: '\
                    % ({'i': str(i)})))

                ovl_type = self.guess_overlay_type(sources[0])
                correct = self.get_ans('Is %(type)s the correct overlay'\
                                ' type?: ' % ({'type': ovl_type}))
                while not ovl_type or not correct:
                    ovl_type = self.check_overlay_type(\
                                self.get_input('Please provide overlay'\
                                ' type: '))
                    correct = True

                sources.append(ovl_type)
                if 'branch' in self.required:
                    sources.append(self.get_input('Define source[%(i)s]\'s '\
                        'branch (if applicable): ' % ({'i': str(i)})))
                else:
                    sources.append('')
            else:
                sources.append(self.get_input('Define source URL: '))

                ovl_type = self.guess_overlay_type(sources[0])
                correct = self.get_ans('Is %(type)s the correct overlay'\
                                ' type?: ' % ({'type': ovl_type}))
                while not ovl_type or not correct:
                    ovl_type = self.check_overlay_type(\
                                   self.get_input('Please provide overlay'\
                                   ' type: '))
                    correct = True

                sources.append(ovl_type)
                if 'branch' in self.required:
                    sources.append(self.get_input('Define source branch (if applicable): '))
                else:
                    sources.append('')
                if self.info_available:
                    sources1, sources2, sources3 = self._set_additional_info(sources)
                    self.overlay['sources'].append(sources2)
                    self.overlay['sources'].append(sources3)
            self.overlay['sources'].append(sources)
        print('')


    def get_owner(self):
        '''
        Prompts user for overlay owner info and
        then appends the values to the overlay
        being created.
        '''
        print('')
        self.overlay['owner_name'] = self.get_input('Define owner name: ')
        self.overlay['owner_email'] = self.get_input('Define owner email: ')
        print('')


    def get_component(self, component, msg):
        '''
        Sets overlay component value.

        @params component: (str) component to be set
        @params msg: (str) prompt message for component
        '''
        if component not in ('branch', 'type'):
            if component in ('descriptions', 'feeds', 'name', 'owner', 'sources'):
                getattr(self, 'get_%(comp)s' % ({'comp': component}))()
            else:
                self.overlay[component] = getattr(self, 'get_input')(msg)


    def get_overlay_components(self):
        '''
        Acquires overlay components via user interface.
        '''
        self.overlay = {}

        for component in self.required:
            self.get_component(component, 'Define %(comp)s: '\
                                % ({'comp': component}))


    def read(self, path):
        '''
        Reads overlay.xml files and appends the contents
        to be sorted when writing to the file.

        @params path: path to file to be read
        '''
        try:
            document = ET.parse(path)
        except xml.etree.ElementTree.ParseError as error:
            msg = 'Interactive.read(); encountered error: %(error)s'\
                % ({'error': error})
            raise Exception(msg)

        overlays = document.findall('overlay') + document.findall('repo')

        for overlay in overlays:
            ovl_name = overlay.find('name')
            ovl = Overlay.Overlay(config=self.config, xml=overlay, ignore=1)
            self.overlays.append((ovl_name.text, ovl))


    def _set_additional_info(self, source):
        '''
        Sets additional overlay source info
        based on the URL.
        '''
        sources = self._set_overlay_info(source)
        return sources


    def _set_overlay_info(self, source):
        '''
        Sets additional possible source URLs for both github
        and git.overlays.gentoo.org source URLs.

        @params source: list of the source URL, type, and branch.
        '''
        ssh_type, url = self._split_source_url(source[0])

        if 'github.com' in url[2]:
            github_source = True
        else:
            github_source = False

        if not ssh_type:
            source2_url = url
            # Make the second source URL the ssh URL.
            if 'git:' not in url[:1]:
               source2_url.remove(source2_url[0])
               source2_url.insert(0, 'git:')

            if github_source:
                source2_url = '/'.join(source2_url)
                source2_url = source2_url.replace('://', '@')
                source2_url = source2_url.replace('.com/', '.com:')
                source2 = [source2_url, source[1], source[2]]
            else:
                source2_url = '/'.join(source2_url)
                source2_url = source2_url.replace('git://', 'git+ssh://')
                source2_url = source2_url.replace('git.overlays', 'git@git.overlays')
                source2 = [source2_url, source[1], source[2]]

            # Check to see the next source URL
            # that needs to be created from the
            # URL given.
            if 'git:' in url[:1]:
                next_header = 'https:'
            else:
                next_header = 'git:'
        else:
            # Joining a split ssh URL by '/' turns it into
            # a normal git:// source URL regardless of whether
            # it is github or g.o.g.o.
            source2 = ['/'.join(url), source[1], source[2]]
            next_header = 'https:'

        source3_url = url
        source3_url.remove(source3_url[0])
        source3_url.insert(0, next_header)

        if next_header in 'https:' and 'git.overlays.gentoo.org' in url[2]:
            source3_url.insert(3, 'gitroot')

        source3 = ['/'.join(source3_url), source[1], source[2]]

        info_url = url
        info_url.remove(info_url[0])
        info_url.insert(0, 'https:')

        if github_source:
            p = info_url[4].replace('.git', '')

            home_url = info_url
            atom_url = info_url

            home_tail = p
            atom_tail = p + '/commits/'

            if source[2]:
                home_tail = p + '/tree/' + source[2]
                atom_tail += source[2] + '.atom'
            else:
                atom_tail += 'master.atom'

            home_url.remove(info_url[4])
            home_url.insert(4, home_tail)

            atom_url.remove(info_url[4])
            atom_url.insert(4, atom_tail)

            self.overlay['homepage'] = '/'.join(home_url)
            self.overlay['feeds'] = ['/'.join(atom_url)]
        else:
            if 'gitroot' in info_url:
                info_url.remove('gitroot')
            info_url.insert(3, 'gitweb')

            p = '?p='
            p += info_url[4]
            info_url.remove(info_url[4])
            info_url.insert(4, p)

            home_url = info_url
            atom_url = info_url
            rss_url = info_url

            home_tail = info_url[5]
            atom_tail = info_url[5]
            rss_tail = info_url[5]

            if source[2]:
                home_tail += ';a=shortlog;h=refs/heads/' + source[2]
                atom_tail += ';a=atom;h=refs/heads/' + source[2]
                rss_tail += ';a=rss;h=refs/heads/' + source[2]
            else:
                home_tail += ';a=summary'
                atom_tail += ';a=atom'
                rss_tail += ';a=rss'

            home_url.remove(info_url[5])
            home_url.insert(5, home_tail)

            atom_url.remove(info_url[5])
            atom_url.insert(5, atom_tail)

            rss_url.remove(info_url[5])
            rss_url.insert(5, rss_tail)

            self.overlay['homepage'] = '/'.join(home_url)
            self.overlay['feeds'] = ['/'.join(atom_url), '/'.join(rss_url)]

        return source, source2, source3


    def _split_source_url(self, source_url):
        '''
        Splits the given source URL based on
        the source URL type.

        @params source_url: str, represents the URL for the repo.
        @rtype tuple: indication on whether or not the source was
        a ssh type URL, or not and the newly split url components.
        '''
        ssh_source = True

        if re.search("^(git://)|(http://)|(https://)", source_url):
            source_url = source_url.split('/')
            ssh_source = False
            return (ssh_source, source_url)
        if re.search('^git\+ssh://', source_url):
            source_url = source_url.replace('+ssh', '')
            source_url = source_url.replace('git@', '').split('/')
            return (ssh_source, source_url)
        if re.search('^git@', source_url):
            source_url = source_url.replace('@', '//')
            source_url = source_url.replace(':', '/')
            source_url = source_url.replace('//', '://').split('/')
            return (ssh_source, source_url)

        raise Exception('Interactive._split_source_url(); error: Unable '\
                        'to split URL.')


    def _sort_to_tree(self):
        '''
        Sorts all Overlay objects by overlay name
        and converts the sorted overlay objects to
        XML that is then appended to the tree.
        '''
        self.overlays = sorted(self.overlays)
        for overlay in self.overlays:
            self.tree.append(overlay[1].to_xml())


    def write(self, destination):
        '''
        Writes overlay file to desired location.
        
        @params destination: path & file to write xml to.
        @rtype bool: reflects success or failure to write xml.
        '''
        if not destination:
            filename = self.get_input('Desired overlay file name: ')
            filepath = self.config.get_option('overlay_defs')

            if not filename.endswith('.xml'):
                filename += ".xml"

            if not filepath.endswith('/'):
                filepath += "/"

            destination = filepath + filename

        self.tree = ET.Element('repositories', version='1.0', encoding=_UNICODE)

        if os.path.isfile(destination):
            self.read(destination)

        self._sort_to_tree()
        indent(self.tree)
        self.tree = ET.ElementTree(self.tree)

        try:
            with fileopen(destination, 'w') as xml:
                self.tree.write(xml, encoding=_UNICODE)
            print('Successfully wrote to: %(path)s' % ({'path': destination}))
            return True

        except IOError as e:
            raise Exception("Writing XML failed: %(error)s" % ({'error': e}))
