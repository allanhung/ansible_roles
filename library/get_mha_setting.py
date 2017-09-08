#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_mha_setting
short_description: get mha setting
set_facts: pillar.mha_setting
'''

EXAMPLES = '''
- name: get mha setting
  get_mha_setting: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
