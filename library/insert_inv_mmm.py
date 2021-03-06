#!/usr/bin/python

DOCUMENTATION = '''
---
module: insert_inv_mmm
short_description: insert dba inventory for mmm
'''

EXAMPLES = '''
- name: insert mmm into inventory
  insert_inv_mmm: {}
'''

def main():
    fields = {
        "debug": {"default": False, "type": "bool"}
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
