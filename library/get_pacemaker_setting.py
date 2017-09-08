#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_pacemaker_setting
short_description: get pacemaker setting
set_facts: pillar.pacemaker_setting
'''

EXAMPLES = '''
- name: get pacemaker setting
  get_pacemaker_setting: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
