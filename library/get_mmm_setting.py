#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_mmm_setting
short_description: get mmm setting
set_facts: pillar.mmm_setting
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
