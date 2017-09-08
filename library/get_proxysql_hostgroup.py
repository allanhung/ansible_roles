#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_proxysql_hostgroup
short_description: get proxysql hostgroup
set_facts: pillar.proxysql_hostgroup
'''

EXAMPLES = '''
- name: get proxysql hostgroup
  get_proxysql_hostgroup: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
