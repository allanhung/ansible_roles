#!/usr/bin/python

DOCUMENTATION = '''
---
module: insert_inv_mongodb
short_description: insert dba inventory for mongodb
'''

EXAMPLES = '''
- name: get mongodb setting
  insert_inv_mongo: {}
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
