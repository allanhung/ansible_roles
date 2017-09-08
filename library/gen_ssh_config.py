#!/usr/bin/python

DOCUMENTATION = '''
---
module: gen_ssh_config
short_description: generate ssh config
'''

EXAMPLES = '''
- name: generate ssh config
  gen_ssh_config:
    ssh_config_key: ssh_config
'''

def main():
    fields = {
        "ssh_config_key": {"required": True, "type": "str"},
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
