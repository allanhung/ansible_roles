#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_proxysql_server
short_description: get proxysql server
set_facts: pillar.proxysql_server
'''

EXAMPLES = '''
- name: get proxysql server
  get_proxysql_server: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
