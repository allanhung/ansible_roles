#!/usr/bin/python

DOCUMENTATION = '''
---
module: gen_mysql_base_user
short_description: get mysql base user
set_facts: pillar.mysql_base_user
'''

EXAMPLES = '''
- name: generate mysql base user
  gen_mysql_base_user: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
