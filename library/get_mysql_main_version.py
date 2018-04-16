#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_mysql_main_version
short_description: parse mysql version
set_facts: pillar.mysql_main_version
'''

EXAMPLES = '''
- name: get mysql main version
  get_mysql_main_version:
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
