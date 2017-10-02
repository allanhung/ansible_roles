#!/usr/bin/python

# -*- coding: utf-8 -*-
import codecs
import os
import socket
from collections import defaultdict

from copy import deepcopy
from pyparsing import Literal, White, Word, alphanums, CharsNotIn
from pyparsing import Forward, Group, Optional, OneOrMore, ZeroOrMore
from pyparsing import pythonStyleComment, Empty, Combine
from glob import iglob


DOCUMENTATION = '''
---
module: get_mysql_log
short_description: get mysql log setting
'''

EXAMPLES = '''
- name: get mysql log setting
  get_mysql_log:
    myhost: "{{ myhost }}"
    mode: get_mysql_log
  register: mysql_log
'''

# https://github.com/privacyidea/mysqlparser
class MySQLParser(object):

    key = Word(alphanums + "_-")
    space = White().suppress()
    value = CharsNotIn("\n")
    filename = Literal("!includedir") + Word(alphanums + " /.")
    comment = ("#")
    config_entry = (key + Optional(space)
                    + Optional(
                        Literal("=").suppress() + Optional(space)
                        + Optional(value) + Optional(space)
                        + Optional("#")
                    )
                    )
    single_value = key
    client_block = Forward()
    client_block << Group((Literal("[").suppress()
                          + key
                          + Literal("]").suppress())
                          + Group(ZeroOrMore(Group(config_entry)))
                          )

    include_block = Forward()
    include_block << Group(Combine(filename) +
                           Group(Group(Empty())))

    # The file consists of client_blocks and include_files
    client_file = OneOrMore( include_block| client_block ).ignore(
        pythonStyleComment)
    
    file_header = """# File parsed and saved by privacyidea.\n\n"""
    
    def __init__(self, infile="/etc/mysql/my.cnf",
                 content=None,
                 opener=open):
        self.file = None
        self.opener = opener
        if content:
            self.content = content
        else:
            self.file = infile
            self._read()

    def _read(self):
        """
        Reread the contents from the disk
        """
        with self.opener(self.file, 'rb') as f:
            self.content = f.read().decode('utf-8')

    def get(self):
        """
        return the grouped config
        """
        if self.file:
            self._read()
        config = self.client_file.parseString(self.content)
        return config
    
    def format(self, dict_config):
        '''
        :return: The formatted data as it would be written to a file
        '''
        output = ""
        output += self.file_header
        for section, attributes in dict_config.items():
            if section.startswith("!includedir"):
                output += "{0}\n".format(section)
            else:
                output += "[{0}]\n".format(section)
                for k, v in attributes.iteritems():
                    if v:
                        output += "{k} = {v}\n".format(k=k, v=v)
                    else:
                        output += "{k}\n".format(k=k)

            output += "\n"

        return output

    def get_dict(self, section=None, key=None):
        '''
        return the client config as a dictionary.
        '''
        ret = {}
        config = self.get()
        for client in config:
            client_config = {}
            for attribute in client[1]:
                if len(attribute) > 1:
                    client_config[attribute[0]] = attribute[1]
                elif len(attribute) == 1:
                    client_config[attribute[0]] = None
            ret[client[0]] = client_config
        if section:
            ret = ret.get(section, {})
            if key:
                ret = ret.get(key)
        return ret

    def save(self, dict_config=None, outfile=None):
        if dict_config:
            output = self.format(dict_config)
            with self.opener(outfile, 'wb') as f:
                for line in output.splitlines():
                    f.write(line.encode('utf-8') + "\n")

class MySQLConfiguration(object):
    """
    an object that takes care of collecting the mysql configuration from all included directories

    assumption: a value can be uniquely mapped to a single file! (i.e. the options
    are not overwritten in multiple files)
    """
    def __init__(self, root_filename, opener=open):
        """
        :param root_filename: filename of the configuration file
        :param open: you may pass another function to open files here, e.g. to edit files remotely.
        """
        self._opener = opener
        self.root = MySQLParser(root_filename, opener=opener)
        #: map a key (given as (section, key)) to a MySQLConfiguration instance.
        #: if a key has no entry in _key_map, it is managed in `root`
        self._key_map = {}
        self._children = []
        self._read_config()

    def _read_child_config(self, filename):
        """
        Read configuration from *filename*, store MySQLConfiguration instances in self._children
        and self._key_map
        """
        child_config = MySQLConfiguration(filename, self._opener)
        self._children.append(child_config)
        for section, contents in child_config.get_dict().iteritems():
            for key, value in contents.iteritems():
                location = (section, key)
                if location in self._key_map:
                    raise RuntimeError('Value {!r}/{!r} already found in {!r}'.format(section, value,
                                                                                      self._key_map[location].root.file))
                self._key_map[location] = child_config

    def _read_config(self):
        """
        This initializes `_key_map` and _children.
        """
        self._key_map = {}
        self._children = []
        root_dct = self.root.get_dict()
        base_directory = os.path.dirname(self.root.file)
        for section, contents in root_dct.iteritems():
            # find all !includedir lines, add configuration to self._children and self._sectionmap
            if section.startswith('!includedir'):
                relative_directory = section.split(' ', 1)[1]
                directory = os.path.abspath(os.path.join(base_directory, relative_directory))
                # include all files in the directory
                for filename in iglob(os.path.join(directory, '*.cnf')):
                    # order is not guaranteed, according to mysql docs
                    # parse every file, return parsing result
                    self._read_child_config(filename)
            elif section.startswith('!'):
                raise NotImplementedError()

    def get_dict(self, section=None, key=None):
        """
        Get the MySQL configuration, with !includedir entries purged, and with all included files processed.
        :return:
        """
        dct = self.root.get_dict()
        for dct_key in dct.keys():
            if dct_key.startswith('!'):
                del dct[dct_key]
        # add children
        for child in self._children:
            dct.update(child.get_dict())
        ret = dct
        if section:
            ret = dct.get(section, {})
            if key:
                ret = ret.get(key)
        return ret

    def save(self, new_config):
        """
        write all the config objects in *config* to the right files
        """
        config = deepcopy(new_config)
        # iterate over all values of which we know that they belong in another file
        #: maps MySQLConfiguration objects to configuration
        save_configs = defaultdict(lambda: defaultdict(dict))
        # find all keys which are updated in `config` and delegated to another file
        for (child_section, child_key), child in self._key_map.iteritems():
            # check if `config` contains a value for `child_section` and `child_key`
            if child_section in config:
                child_contents = config[child_section]
                if child_key in child_contents:
                    # delegate the value to the MySQLConfiguration object
                    save_configs[child][child_section][child_key] = config[child_section][child_key]
                    # We have handled this value, remove it from `config`
                    del config[child_section][child_key]
                    # Delete empty sections from `config`
                    if not config[child_section]:
                        del config[child_section]
        # find all keys that are *added* to sections for which entries in _value_map exist
        # (i.e. the section is delegated to another config file)
        # if the section has values in multiple files, one is chosen non-deterministically
        for (child_section, child_key), child in self._key_map.iteritems():
            if child_section in config:
                save_configs[child][child_section].update(config[child_section])
                del config[child_section]
        # all remaining keys in `config` belong in `root`.
        # now, save all children
        for child, child_config in save_configs.iteritems():
            child.save(child_config)
        # add all !includedir directives
        root_dct = self.root.get_dict()
        for key, value in root_dct.iteritems():
            if key.startswith('!'):
                config[key] = value
        # save the local configuration
        self.root.save(config, self.root.file)
        # re-read configuration!
        self._read_config()


def get_mysql_log(**param):
    myhost=param['myhost']
    result={}
    mycnf=MySQLParser("/etc/my.cnf")
    config=mycnf.get_dict()
    for k, v in config.items():
        for m, n in v.items():
            if '-' in m:
                v[m.replace('-','_')]=n
    datadir=config.get("mysqld").get("datadir")
    if "log_error" in config.get("mysqld").keys():
        errlog=config.get("mysqld").get("log_error")
    elif "mysqld_safe" in config.keys() and "log_error" in config.get("mysqld_safe").keys():
        errlog=config.get("mysqld_safe").get("log_error")
    else:
        errlog=socket.gethostname()+'.err'
    if errlog[:1]<>'/':
        errlog=os.path.join(datadir,errlog)
    # slow log
    if "slow_query_log" in config.get("mysqld").keys():
        slowlog=config.get("mysqld").get("slow_query_log_file") if "slow_query_log_file" in config.get("mysqld").keys() else socket.gethostname()+'-slow.log'
    else:
        slowlog=''
    if slowlog[:1]<>'/' and slowlog:
        slowlog=os.path.join(datadir,slowlog)
    result['data_dir']=datadir
    result['error_log']=errlog
    result['slow_log']=slowlog
    return result

def main():

    fields = {
        "myhost": {"required": True, "type": "dict"},
        "mode": {
          "default": "get_mysql_log",
          "choices": ["get_mysql_log"],
          "type": "str"
        },
    }

    choice_map = {
        "get_mysql_log": get_mysql_log
    }

    module = AnsibleModule(argument_spec=fields)
    result = choice_map.get(module.params['mode'])(**module.params)
    module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
