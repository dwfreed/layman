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

import sys

from   layman.api            import LaymanAPI
from   layman.compatibility  import fileopen
from   layman.config         import BareConfig
from   layman.utils          import indent

#py3
if sys.hexversion >= 0x30200f0:
    _UNICODE = 'unicode'
else:
    _UNICODE = 'UTF-8'

class Main(object):

    def __init__(self):
        self.config = BareConfig()
        self.overlay = {}
        self.supported_types = LaymanAPI(config=self.config).supported_types()

    def __call__(self):

        repo = ET.Element('repositories', version='1.0', encoding=_UNICODE)

        for x in range(1, int(self.get_input("How many overlays would you like to create?: "))+1):
            print('')
            print('Overlay #%(x)s: ' % ({'x': str(x)}))
            print('~~~~~~~~~~~~~')

            self.get_overlay_components()
            ovl = Overlay.Overlay(config=self.config, ovl_dict=self.overlay, ignore=1)
            repo.append(ovl.to_xml())

        indent(repo)
        self.tree = ET.ElementTree(repo)
        self.write()


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
        print('Supported types include: %(types)s.' % ({'types': ', '.join(self.supported_types)}))
        return None


    def update_required(self):
        '''
        Prompts user for optional components and updates
        the required components accordingly.
        '''
        possible_components = ['name', 'description', 'homepage', 'owner', 'quality',
                           'priority', 'sources', 'branch', 'irc', 'feed']

        for possible in possible_components:
            if possible not in self.required:
                available = self.get_ans("Include %(comp)s for this overlay? [y/n]: " \
                    % ({'comp': possible}))
                if available:
                    self.required.append(possible)


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


    def get_sources(self):
        '''
        Prompts user for possible overlay source
        information such as type, url, and branch
        and then appends the values to the overlay
        being created.
        '''
        ovl_type = None
        source_amount = int(self.get_input('How many sources exist for this overlay?: '))

        while not ovl_type:
            ovl_type = self.check_overlay_type(self.get_input('Define overlay\'s type: '))

        self.overlay['sources'] = []

        for i in range(1, source_amount + 1):
            sources = []
            if source_amount > 1:
                sources.append(self.get_input('Define source[%(i)s] URL: '\
                    % ({'i': str(i)})))
                sources.append(ovl_type)
                if 'branch' in self.required:
                    sources.append(self.get_input('Define source[%(i)s]\'s '\
                        'branch (if applicable): ' % ({'i': str(i)})))
                else:
                    sources.append('')
            else:
                sources.append(self.get_input('Define source URL: '))
                sources.append(ovl_type)
                if 'branch' in self.required:
                    sources.append(self.get_input('Define source branch (if applicable): '))
                else:
                    sources.append('')

            self.overlay['sources'].append(sources)
        print('')

    def get_overlay_components(self):
        '''
        Acquires overlay components via user interface.
        '''
        self.update_required()

        for component in self.required:

            if 'feeds' in component:
                self.get_feeds(overlay)
                print('')

            elif 'name' in component:
                print('')
                self.overlay['name'] = self.get_input('Define overlay name: ')

            elif 'owner' in component:
                print('')
                self.overlay['owner_name'] = self.get_input('Define owner name: ')
                self.overlay['owner_email'] = self.get_input('Define owner email: ')
                print('')

            elif 'sources' in component:
                self.get_sources()

            else:
                if 'type' not in component and 'branch' not in component:
                    self.overlay[component] = self.get_input('Define %(comp)s: '\
                        % ({'comp': component}))


    def write(self):
        '''
        Writes overlay file to desired location.
        '''
        print('')
        filename = self.get_input('Desired overlay file name: ')
        filepath = self.get_input('Desired output path: ')

        if not filename.endswith('.xml'):
            filename += ".xml"

        if not filepath.endswith('/'):
            filepath += "/"

        destination = filepath + filename
        try:
            with fileopen(destination, 'w') as xml:
                self.tree.write(xml, encoding=_UNICODE)

        except IOError as e:
            print("Writing XML failed: %(error)s" % ({'error': e}))

