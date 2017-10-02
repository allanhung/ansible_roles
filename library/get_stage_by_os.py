#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_stage_by_os
short_description: get stage by os
'''

EXAMPLES = '''
- name: get_stage_by_os
  get_stage_by_os:
    role_name: nx_log
'''

def main():
    fields = {
        "role_name": {"required": True, "type": "str"},
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
