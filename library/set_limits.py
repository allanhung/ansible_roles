#!/usr/bin/python

DOCUMENTATION = '''
---
module: set_limits
short_description: set limits config to facts
'''

EXAMPLES = '''
- name: set root limits
  set_limits:
    limits_key: root_limits
'''

def main():
    fields = {
        "limits_key": {"required": True, "type": "str"},
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
