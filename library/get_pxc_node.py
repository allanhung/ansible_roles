#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_pxc_node
short_description: get pxc node list
set_facts: pillar.pxc_node_list
'''

EXAMPLES = '''
- name: generate mysql config
  get_pxc_node: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
