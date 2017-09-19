#!/usr/bin/python

DOCUMENTATION = '''
---
module: insert_inv_rd
short_description: insert dba inventory for rd
'''

EXAMPLES = '''
- name: get mmm setting
  get_mmm_setting: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
