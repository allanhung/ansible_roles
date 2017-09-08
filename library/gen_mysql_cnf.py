#!/usr/bin/python

DOCUMENTATION = '''
---
module: gen_mysql_cnf
short_description: generate mysql config
set_facts: pillar.mysql_cnf
'''

EXAMPLES = '''
- name: generate mysql config
  gen_mysql_cnf:
    mysql_version: "{{ mysql_version }}"
'''

def main():
    fields = {
        "mysql_version": {"required": True, "type": "str"},
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
