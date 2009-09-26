#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Based on the work of Sebastian Rittau: http://www.rittau.org/blog/20070726-01

import sys, optparse, getpass, traceback
import gtk # ensure that the application name is correctly set
import gnomekeyring as gkey

_version = '0.1.0'

class CLI(object):
    ''' Class providing command-line interface '''
    # operational modes
    unknown = 0
    SET = 1
    GET = 2
    
    def __init__(self):
        self.keyring = Keyring()
        self.mode = CLI.unknown
        self.options = None
        self.args = None
    
    def parse_args(self):
        ''' Parse commandline options. 
        
        Returns False if something is wrong.
        '''
        
        parser = optparse.OptionParser()
        parser.version = _version
        parser.set_usage('''%(program)s [get|set] [options]
        
Use 'get' for retrieving credentials from GNOME keyring 
and 'set' for storing credentials into the keyring.

Example usage: %(program)s get -s myserver.com -p ftp''' \
% {'program': sys.argv[0]})
        
        parser.add_option('--version', action='store_true', 
                          help='print program version and exit');
        
        get_group = optparse.OptionGroup(parser, 
                                         "Options to be used for 'get'")
        get_group.add_option('-s', '--server', help='network server')
        get_group.add_option('-p', '--protocol', help='network protocol')
        get_group.add_option('-u', '--user', help='username')
        
        set_group = optparse.OptionGroup(parser,
                    "Options to be used for 'set'", "Notice: Also all "
                    "options for 'get' can be used here. Mandatory options "
                    "are: protocol, server, user.")
        set_group.add_option('-w', '--password', help='password (you will be '
                             'asked if not specified)')
        set_group.add_option('-t', '--port', help='network port')
        set_group.add_option('-d', '--domain', help='network domain')
        set_group.add_option('-k', '--keyring', help='keyring name (will use '
                             'default one when no specified)')
        
        parser.add_option_group(get_group)
        parser.add_option_group(set_group)            
        
        try:
            if sys.argv[1] == 'set':
                self.mode = CLI.SET
                del sys.argv[1]
            elif sys.argv[1] == 'get':
                self.mode = CLI.GET
                del sys.argv[1]
        except IndexError:
            pass
        
        (options, args) = parser.parse_args()
        self.options, self.args = options, args
        
        if options.version:
            parser.print_version()
            sys.exit(0)
            
        if self.mode == CLI.unknown:
            parser.error("Must specify 'get' or 'set' as first argument! "
                         'See --help.')
        
        if self.mode == CLI.SET:
            if not options.password:
                # ask for password
                options.password = getpass.getpass()
            # check mandatory options
            set_mandatory = ['server', 'protocol', 'user', 'password']
            for mand in set_mandatory:
                if options.__dict__[mand] == None:
                    parser.error('Mandatory option is missing! See --help.')
        
        return True
        
    def execute(self):
        ''' Run the interface '''
        
        if not self.parse_args():
            sys.exit(2)
            
        if self.mode == CLI.GET:
            self._query()
        elif self.mode == CLI.SET:
            self._create()
            
        sys.exit(0)
            
    def _query(self):
        ''' Get credentials from keyring '''
        
        o = self.options
        matches = self.keyring.get_credentials(o.server, o.protocol, o.user)
        if not matches:
            sys.exit(3)
        
        print >>sys.stderr, '# server [TAB] user [TAB] password'
        for match in matches:
            line = '%s:%s' % (match['protocol'], match['server'])
            if 'port' in match:
                line += ':%s' % match['port']
            line += '\t%s\t%s' % (match['user'], match['password'])
            print line
        
    def _create(self):
        ''' Store credentials into keyring '''
        
        o = self.options
        try:
            self.keyring.set_credentials(o.server, o.protocol, o.user, 
                                o.password, o.port, o.domain, o.keyring)
        except KeyringError as e:
            print >>sys.stderr, 'Error creating keyring item'
            traceback.print_exc(file=sys.stderr)
            sys.exit(4)
        

class Keyring(object):
    '''
    Class for accessing GNOME keyring items containing network passwords.
    '''
    
    def has_credentials(self, server=None, protocol=None, user=None):
        ''' Check whether some credentials exist matching specified parameters.
        
        Returns True or False. Always returns False if no parameter specified.
        '''
        
        items = self.get_credentials(server=server, protocol=protocol, 
                                     user=user)
        return len(items) > 0

    def get_credentials(self, server=None, protocol=None, user=None):
        ''' Get all credentials matching specified parameters.
        
        Returns list of matches. Each match is a dictionary. Returns empty list
        if nothing matching found. Always returns empty list if no parameter
        specified.
        '''
        
        try:
            attrs = {'server': server, 'protocol': protocol, 'user': user}
            items = gkey.find_network_password_sync(**attrs)
        except gkey.Error:
            return []
        else:
            return items

    def set_credentials(self, server, protocol, user, password, port=None, 
                        domain=None, keyring=None):
        ''' Create a new item in the keyring.
        
        A default keyring is used if no keyring is specified. A KeyringError
        is thrown if item can't be created.
        '''
        
        try:
            def_keyring = gkey.get_default_keyring_sync()
            attrs = {'server': server, 'protocol': protocol, 'user': user,
                     'password': password, 'domain': domain,
                     'keyring': keyring or def_keyring}
            if port:
                attrs['port'] = int(port)
            gkey.set_network_password_sync(**attrs)
        except (gkey.Error, TypeError) as e:
            raise KeyringError('Error setting credentials', e)
            
            
class KeyringError(Exception):
    ''' Base exception for all errors coming from this module. '''


if __name__ == '__main__':
    try:
        c = CLI()
        c.execute()
    except KeyboardInterrupt:
        print 'Interrupted, exiting...'
        sys.exit(1)
