#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_replication
short_description: generate mysql replication setting
set_facts: pillar.mysql_replication
'''

EXAMPLES = '''
- name: get_replication
  get_replication:
    master_hostvars: "{{ hostvars[pillar['mysql_replication']['master_host']] }}"
'''

def main():
    fields = {
        "master_hostvars": {"required": True, "type": "dict"},
    }
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
