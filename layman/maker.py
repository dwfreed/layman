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
from   layman.utils          import get_ans, get_input, indent, reload_config

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
        self.output = self.config.get_option('output')
        self.overlay = {}
        self.overlays = []
        self.overlays_available = self.layman_inst.get_available()
        self.supported_types = self.layman_inst.supported_types().keys()

    def __call__(self, overlay_package=None, path=None):

        if not overlay_package:
            msg = 'How many overlays would you like to create?: '
            for x in range(1, int(get_input(msg))+1):
                self.info_available = False
                self.output.notice('')
                self.output.info('Overlay #%(x)s: ' % ({'x': str(x)}))
                self.output.info('~~~~~~~~~~~~~')

                msg = 'Is the mirror for this overlay either github.com,'
                self.output.info(msg)
                msg = 'git.overlays.gentoo.org, or bitbucket.org? [y/n]: '
                self.info_available = get_ans(msg)

                self.output.notice('')
                self.update_required()
                self.output.notice('')
                self.get_overlay_components()
                ovl = Overlay.Overlay(config=self.config, ovl_dict=self.overlay, ignore=1)
                self.overlays.append((self.overlay['name'], ovl))
        else:
            ovl_name, ovl = overlay_package
            self.overlays.append((ovl_name, ovl))

        result = self.write(path)
        return result


    def check_overlay_type(self, ovl_type):
        '''
        Validates overlay type.

        @params ovl_type: str of overlay type
        @rtype None or str (if overlay type is valid).
        '''
        if ovl_type.lower() in self.supported_types:
            return ovl_type.lower()

        msg = '!!! Specified type "%(type)s" not valid.' % ({'type': ovl_type})
        self.output.warn(msg)
        msg = 'Supported types include: %(types)s.'\
              % ({'types': ', '.join(self.supported_types)})
        self.output.warn(msg)
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
                    available = get_ans(msg)
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

        desc = get_input('Define overlay\'s description: ')
        descriptions.append(desc)

        self.overlay['descriptions'] = descriptions


    def get_feeds(self):
        '''
        Prompts user for any overlay RSS feeds
        and updates overlay dict with values.
        '''
        msg = 'How many RSS feeds exist for this overlay?: '
        feed_amount = int(get_input(msg))
        feeds = []

        for i in range(1, feed_amount + 1):
            if feed_amount > 1:
                msg = 'Define overlay feed[%(i)s]: ' % ({'i': str(i)})
                feeds.append(get_input(msg))
            else:
                feeds.append(get_input('Define overlay feed: '))

        self.overlay['feeds'] = feeds
        self.output.notice('')


    def get_name(self):
        '''
        Prompts user for the overlay name
        and updates the overlay dict.
        '''
        name = get_input('Define overlay name: ')

        while name in self.overlays_available:
            msg = '!!! Overlay name already defined in list of installed'\
                  ' overlays.'
            self.output.warn(msg)
            msg = 'Please specify a different overlay name: '
            name = get_input(msg, color='yellow')

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
            msg = 'How many different sources, protocols, or mirrors exist '\
                  'for this overlay?: '
            source_amount = int(get_input(msg))

        self.overlay['sources'] = []

        for i in range(1, source_amount + 1):
            sources = []
            if source_amount > 1:
                msg = 'Define source[%(i)s]\'s URL: ' % ({'i': str(i)})
                sources.append(get_input(msg))

                ovl_type = self.guess_overlay_type(sources[0])
                msg = 'Is %(type)s the correct overlay type?: '\
                    % ({'type': ovl_type})
                correct = get_ans(msg)
                while not ovl_type or not correct:
                    msg = 'Please provide overlay type: '
                    ovl_type = self.check_overlay_type(\
                                get_input(msg, color='yellow'))
                    correct = True

                sources.append(ovl_type)
                if 'branch' in self.required:
                    msg = 'Define source[%(i)s]\'s branch (if applicable): '\
                          % ({'i': str(i)})
                    sources.append(get_input(msg))
                else:
                    sources.append('')
            else:
                sources.append(get_input('Define source URL: '))

                ovl_type = self.guess_overlay_type(sources[0])
                msg = 'Is %(type)s the correct overlay type?: '\
                       % ({'type': ovl_type})                                                      
                correct = get_ans(msg)
                while not ovl_type or not correct:
                    msg = 'Please provide overlay type: '
                    ovl_type = self.check_overlay_type(\
                                   get_input(msg, color='yellow'))
                    correct = True

                sources.append(ovl_type)
                if 'branch' in self.required:
                    msg = 'Define source branch (if applicable): '
                    sources.append(get_input(msg))
                else:
                    sources.append('')
            if self.info_available:
                sources = self._set_additional_info(sources)
                for source in sources:
                    self.overlay['sources'].append(source)
            else:
                self.overlay['sources'].append(sources)
        self.output.notice('')


    def get_owner(self):
        '''
        Prompts user for overlay owner info and
        then appends the values to the overlay
        being created.
        '''
        self.output.notice('')
        self.overlay['owner_name'] = get_input('Define owner name: ')
        self.overlay['owner_email'] = get_input('Define owner email: ')
        self.output.notice('')


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
                self.overlay[component] = getattr(layman.utils, 'get_input')(msg)


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


    def _set_bitbucket_info(self, source, git=False):
        '''
        Sets overlay info such as extra source URLs, homepage, and
        source feed information for bitbucket.org mirrors.

        @params source: list of the source URL, type, and branch.
        '''
        if git:
            home_url = source[0].replace('.git', '')
            self.overlay['homepage'] = home_url

            return None
        ssh_type, url = self._split_source_url(source[0])
        source2_url = '/'.join(url)

        home_url = source2_url

        if ssh_type:
            home_url = home_url.replace('ssh:', 'https:')
            home_url = home_url.replace('hg@bitbucket.org', 'bitbucket.org')
            source2_url = home_url
        else:
            # Make the second source URL the ssh URL.
            source2_url = source2_url.replace('https:', 'ssh:')
            source2_url = source2_url.replace('bitbucket.org', 'hg@bitbucket.org')

        source2 = [source2_url, source[1], source[2]]

        self.overlay['homepage'] = home_url
        self.overlay['feeds'] = [home_url+'/atom', home_url+'/rss']

        return source2


    def _set_gentoo_info(self, source):
        '''
        Sets overlay info such as extra source URLs, homepage, and
        source feed information for git.overlays.gentoo.org mirrors.

        @params source: list of the source URL, type, and branch.
        '''
        ssh_type, url = self._split_source_url(source[0])

        if not ssh_type:
            source2_url = url
            # Make the second source URL the ssh URL.
            if 'git:' not in url[:1]:
                source2_url.remove(source2_url[0])
                source2_url.insert(0, 'git:')

            source2_url = '/'.join(source2_url)
            source2_url = source2_url.replace('git://', 'git+ssh://')
            source2_url = source2_url.replace('git.overlays', 'git@git.overlays')
            source2 = [source2_url, source[1], source[2]]

            if 'git:' in url[:1]:
                next_header = 'https:'
            else:
                next_header = 'git:'
        else:
            # Joining a split ssh URL by '/' turns it into
            # a normal git:// source URL regardless of the
            # mirror being github, or g.o.g.o.
            source2 = ['/'.join(url), source[1], source[2]]
            next_header = 'https:'

        source3_url = url
        source3_url.remove(source3_url[0])
        source3_url.insert(0, next_header)

        if next_header in 'https:':
            source3_url.insert(3, 'gitroot')

        source3 = ['/'.join(source3_url), source[1], source[2]]

        info_url = url
        info_url.remove(info_url[0])
        info_url.insert(0, 'https:')

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

        return source2, source3


    def _set_github_info(self, source):
        '''
        Sets overlay info such as extra source URLs, homepage, and
        source feed information for github.com mirrors.

        @params source: list of the source URL, type, and branch.
        '''
        ssh_type, url = self._split_source_url(source[0])

        if not ssh_type:
            source2_url = url
            # Make the second source URL the ssh URL.
            if 'git:' not in url[:1]:
                source2_url.remove(source2_url[0])
                source2_url.insert(0, 'git:')

            source2_url = '/'.join(source2_url)
            source2_url = source2_url.replace('://', '@')
            source2_url = source2_url.replace('.com/', '.com:')
            source2 = [source2_url, source[1], source[2]]

            if 'git:' in url[:1]:
                next_header = 'https:'
            else:
                next_header = 'git:'
        else:
            # Joining a split ssh URL by '/' turns it into
            # a normal git:// source URL regardless of the
            # mirror being github, or g.o.g.o.
            source2 = ['/'.join(url), source[1], source[2]]
            next_header = 'https:'

        source3_url = url
        source3_url.remove(source3_url[0])
        source3_url.insert(0, next_header)
        source3 = ['/'.join(source3_url), source[1], source[2]]

        info_url = url
        info_url.remove(info_url[0])
        info_url.insert(0, 'https:')

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

        return source2, source3


    def _set_overlay_info(self, source):
        '''
        Sets additional possible overlay information.

        @params source: list of the source URL, type, and branch.
        '''
        # If the source isn't support but the user said it
        # was then just return the original source.
        sources = [source]

        if 'github.com' in source[0]:
            additional_sources = self._set_github_info(source)
            for source in additional_sources:
                sources.append(source)
        if 'git.overlays.gentoo.org' in source[0]:
            addtional_sources = self._set_gentoo_info(source)
            for source in addtional_sources:
                sources.append(source)
        if 'bitbucket.org' in source[0]:
            source2 = self._set_bitbucket_info(source, git='git' in source[1])
            if 'git' in source[1]:
                sources.append(source2)

        return sources


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
        if re.search('^ssh://', source_url):
            return (ssh_source, source_url.split('/'))

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
            filename = get_input('Desired overlay file name: ')
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
            msg = 'Successfully wrote repo(s) to: %(path)s'\
                  % ({'path': destination})
            self.output.info(msg)
            return True

        except IOError as e:
            raise Exception("Writing XML failed: %(error)s" % ({'error': e}))
