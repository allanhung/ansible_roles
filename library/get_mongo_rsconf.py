#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_mha_conf
short_description: get mongodb replica set config
set_facts: pillar.mongo_rsconf
'''

EXAMPLES = '''
- name: get mha config
  get_mha_conf: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
