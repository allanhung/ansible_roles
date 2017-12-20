#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_service_group
short_description: get service from hostgroup
'''

EXAMPLES = '''
- name: get_service_group
  get_service_group: {}
'''

def main():
    fields = { }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
