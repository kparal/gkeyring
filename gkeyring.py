#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# A small Python tool for shell access to GNOME keyring. It provides
# simple querying for and creating of keyring items.
#
# Author: Kamil Páral <kamil.paral /at/ gmail /dot/ com>, 2009-2014
#
# This program is a free software, licensed under GNU AGPL 3:
# http://www.gnu.org/licenses/agpl-3.0.html

__version__ = '0.4'

import sys
import argparse
import getpass

# Some gnome-keyring documentation:
# http://blogs.codecommunity.org/mindbending/bending-gnome-keyring-with-python-part-2/
# https://developer.gnome.org/gnome-keyring/stable/
import gnomekeyring as gk


class CLI(object):
    ''' Class providing command-line interface for GNOME keyring '''

    ITEM_TYPES = {
        'generic': gk.ITEM_GENERIC_SECRET,
        'network': gk.ITEM_NETWORK_PASSWORD,
        'note': gk.ITEM_NOTE
        }

    def __init__(self):
        self.options = None
        self.keyring = None
        self.params = {}
        self.id = None
        self.item_type = None
        self.secret = None
        self.name = None
        self.output = None

    def parse_args(self):
        ''' Parse commandline options.

        Returns False if something is wrong.
        '''

        desc=\
'''By default %(prog)s queries the GNOME keyring for items matching specified
arguments. You can define the item exactly by --id, or search for it using
--name, -p and/or -i.

It is important to understand that the keyring items are divided into several
types (see --type) and each contain several properties. Both the item type and
item properties can be inspected using a tool like Seahorse. Then you will know
what to query for.

Zero or more items may match your query. They will be printed out one item
a line, by default in the format:
ID [TAB] secret

You can also create a new keyring item using --set. In this case the arguments
-p and/or -i will be used as properties of the new item.

When a new keyring item is created, its ID is printed out on the output.'''

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter)
        parser.description = desc % {'prog': parser.prog}

        parser.add_argument('--version', action='version', version=__version__)
        parser.add_argument('-t', '--type', choices=CLI.ITEM_TYPES.keys(),
            default='generic', help='type of keyring item: '
            'generic, network or note [default: %(default)s]')
        parser.add_argument('-k', '--keyring', help='keyring name [default: '
            'default keyring]', dest=self.keyring)
        parser.add_argument('--id', type=int, nargs='+',
            help='key ID, separate multiple with a space')
        parser.add_argument('-n', '--name',
            help='keyring item descriptive name [exact match for querying, '
            'mandatory if --set]')
        parser.add_argument('-p', default='',
            metavar='PARAM1=VALUE1,PARAM2=VALUE2', dest='params',
            help='params and values of keyring item, e.g. user, server, '
            'protocol, etc.')
        parser.add_argument('-i', default='',
            metavar='PARAM1=VALUE1,PARAM2=VALUE2', dest='params_int',
            help='same as -p, but values are treated as integers, not strings')
        parser.add_argument('--all', action='store_true', help="Don't query for "
            "specific keyring items, list all of them")

        out_group = parser.add_argument_group('Formatting output for '
            'querying keyring items')
        out_group.add_argument('-o', '--output', default='id,name,secret',
            help='comma-separated list of columns to be printed on the output. '
            "Column name may include keywords 'id', 'name', 'secret' or "
            "any item's property name (displayed only when available). Columns "
            "will be separated by tabs. [default: %(default)s]")
        out_group.add_argument('-O', '--output-attribute-names', action='store_true',
            help='show attribute names in addition to values')
        out_group.add_argument('-l', '--no-newline', action='store_true',
            help="don't output the trailing newline")
        out_group.add_argument('-1', action='store_true', dest='output1',
            help="same as '--output secret --no-newline'")

        other_group = parser.add_argument_group('Other operations')
        other_group.add_argument('-s', '--set', action='store_true',
            help='create a new item in the keyring instead of querying')
        other_group.add_argument('-d', '--delete', action='store_true',
            help="delete the item in the keyring identified by '--id'")
        other_group.add_argument('--lock', action='store_true',
            help='lock the keyring')
        other_group.add_argument('--unlock', action='store_true',
            help='unlock the keyring')
        other_group.add_argument('-w', '--password',
            help='provide a password for operations that require it; otherwise'
                 'you will be asked for it interactively')

        epilog=\
"""Example usage:
$ %(prog)s --all
List all keyring items in the default keyring.

$ %(prog)s --id 12
Get keyring item with ID 12 in default keyring.

$ %(prog)s --id 12 21
Get keyring items with ID's 12 and 21 in default keyring.

$ %(prog)s --name 'backup'
Search for keyring item with name 'backup'. You can easily see item names e.g.
in the overview of Seahorse application.

$ %(prog)s -p account_name=my@jabber.org -i gajim=1 -1
Search for keyring item with property 'account_name' with value 'my@jabber.org'
and property 'gajim' with integer value '1'. Output only the secret(s).

$ %(prog)s --type network -p server=my.com,protocol=ftp --output user,secret
Search for network keyring item with 'server' and 'protocol' properties. Output
property 'user' followed by item's secret.

$ %(prog)s --set --name 'foo' -p bar=baz --keyring login
Create a new item in keyring 'login' with name 'foo' and property 'bar'.

$ %(prog)s --delete --id 12
Delete a keyring item with ID 12.

$ %(prog)s --delete --id 12 21
Delete keyring items with ID's 12 and 21.

$ %(prog)s --lock --keyring login
Lock keyring 'login'.

$ %(prog)s --unlock --password qux
Unlock the default keyring and provide the password 'qux' on the command-line.
"""
        parser.epilog = epilog % {'prog': parser.prog}
        options = parser.parse_args()
        self.options = options

        # ensure that the application name is correctly set
        # this must be done after parsing args, because
        # our --name option collides with gtk option --name
        import gtk

        if not gk.is_available():
            print >>sys.stderr, 'GNOME keyring is not available!'
            return False

        # validate mandatory options
        query_mode = not (options.set or options.delete or
                          options.lock or options.unlock)
        if query_mode:
            if not (options.params or options.params_int or options.name or
                    options.id or options.all):
                parser.error('Missing --name, -p, -i, --id or --all! See --help.')

        if options.set:
            if not options.name:
                parser.error('Missing --name! See --help.')

        if options.delete:
            if not options.id:
                parser.error('Missing --id! See --help.')

        # parse string params
        try:
            tuples = options.params.split(',')
            for tupl in tuples:
                if not tupl:
                    # empty string
                    continue
                name, val = tupl.split('=',1)
                self.params[name] = val
        except ValueError, e:
            parser.error('Incorrect syntax of "-p param1=value1,'
                'param2=value2"! See --help.\nDetails:\n%s' % e)

        # parse integer params
        try:
            tuples = options.params_int.split(',')
            for tupl in tuples:
                if not tupl:
                    # empty string
                    continue
                name, val = tupl.split('=',1)
                val = int(val)
                self.params[name] = val
        except ValueError, e:
            parser.error('Incorrect syntax of "-i param1=value1,'
                'param2=value2"! See --help.\nDetails:\n%s' % e)

        if options.keyring:
            self.keyring = options.keyring
        else:
            self.keyring = gk.get_default_keyring_sync()

        if options.output1:
            options.output = 'secret'
            options.no_newline = True

        if (options.set or options.unlock) and not options.password:
            # ask for password
            options.password = getpass.getpass()

        self.secret = options.password
        self.id = options.id
        self.name = options.name
        self.item_type = CLI.ITEM_TYPES[options.type]
        self.output = options.output.split(',')
        self.no_newline = options.no_newline
        self.output_attribute_names = options.output_attribute_names

        return True

    def execute(self):
        ''' Run the interface '''

        if not self.parse_args():
            sys.exit(2)

        if self.options.set:
            ret = self.create()
        elif self.options.delete:
            ret = self.delete()
        elif self.options.lock:
            ret = self.lock();
        elif self.options.unlock:
            ret = self.unlock();
        else:
            ret = self.query()

        sys.exit(0 if ret else 5)

    def query(self):
        ''' Match keyring items from keyring.

        Return True if something was matched, False otherwise.
        '''

        results = []

        try:
            if self.id:
                for item_id in self.id:
                    info = gk.item_get_info_sync(self.keyring, item_id)
                    attr = gk.item_get_attributes_sync(self.keyring, item_id)
                    result = {'id': item_id, 'secret': info.get_secret(),
                              'name': info.get_display_name(), 'attr': attr}
                    results.append(result)
            else:
                matches = gk.find_items_sync(self.item_type, self.params)
                for match in matches:
                    if match.keyring != self.keyring:
                        continue
                    result = {'id': match.item_id, 'secret': match.secret,
                              'attr': match.attributes}
                    info = gk.item_get_info_sync(match.keyring, match.item_id)
                    result['name'] = info.get_display_name()
                    # filter by name if desired
                    if not self.name or self.name == result['name']:
                        results.append(result)
        except gk.Error as e:
            print >>sys.stderr, e.__class__.__name__, e.message
            pass

        if not results:
            return False

        for index, result in enumerate(results):
            if index > 0:
                print

            for index2, tab in enumerate(self.output):
                if index2 > 0:
                    sys.stdout.write('\t')

                if self.output_attribute_names:
                    sys.stdout.write(tab + '=')

                out = None
                if tab == 'id':
                    out = result['id']
                elif tab == 'secret':
                    out = result['secret']
                elif tab == 'name':
                    out = result['name']
                elif tab in result['attr']:
                    out = result['attr'][tab]

                if out:
                    sys.stdout.write(str(out))

        if not self.no_newline:
            print

        return True

    def create(self):
        ''' Create a new keyring item.

        Return True if item created successfully, False otherwise.
        '''

        try:
            item_id = gk.item_create_sync(self.keyring, self.item_type,
                self.name, self.params, self.secret, False)
        except gk.Error, e:
            print >>sys.stderr, 'Error creating keyring item!\nDetails:\n%s'%e
            return False

        print item_id

        return True

    def delete(self):
        ''' Delete a keyring item.

        Return True if item created successfully, False otherwise.
        '''
        for item_id in self.id:
            try:
                gk.item_delete_sync(self.keyring, item_id)
            except gk.Error, e:
                print >>sys.stderr, 'Error deleting keyring item!\nDetails:\n%s'%e
                return False

        return True

    def lock(self):
        '''Lock a keyring.
        '''

        try:
            gk.lock_sync(self.keyring)
        except gk.Error, e:
            print >>sys.stderr, 'Error locking keyring!\nDetails:\n%s'%e
            return False

        return True

    def unlock(self):
        '''Unlock a keyring.
        '''

        try:
            gk.unlock_sync(self.keyring, self.secret)
        except gk.Error, e:
            print >>sys.stderr, 'Error unlocking keyring!\nDetails:\n%s'%e
            return False

        return True


def main():
    '''Main program loop'''
    try:
        c = CLI()
        c.execute()
    except KeyboardInterrupt:
        print 'Interrupted, exiting...'
        sys.exit(1)


if __name__ == '__main__':
    main()
