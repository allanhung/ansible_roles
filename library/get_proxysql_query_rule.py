#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_proxysql_query_rule
short_description: get proxysql query rule
set_facts: pillar.proxysql_qry_rule
'''

EXAMPLES = '''
- name: get proxysql query rule
  get_proxysql_query_rule: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
