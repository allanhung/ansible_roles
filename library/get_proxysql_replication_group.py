#!/usr/bin/python

DOCUMENTATION = '''
---
module: get_proxysql_replication_group
short_description: get proxysql replicatiion group
set_facts: pillar.proxysql_replication_group
'''

EXAMPLES = '''
- name: get proxysql replication group
  get_proxysql_replication_group: {}
'''

def main():
    fields = {}
    module = AnsibleModule(argument_spec=fields)
    module.exit_json(changed=False)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

EXAMPLES = '''
- name: get proxysql group
  get_proxysql:
    mha_setting: "{{ mha.meta }}"
    proxysql_group: "{{ proxysql_group.meta }}"
    mode: get_group
  register: pgroup

- name: get proxysql server
  get_proxysql:
    mha_setting: "{{ mha.meta }}"
    proxysql_group: "{{ proxysql_group.meta }}"
    mode: get_server
  register: pserver

- name: get proxysql query rule
  get_proxysql:
    mha_setting: "{{ mha.meta }}"
    proxysql_group: "{{ proxysql_group.meta }}"
    proxysql_query_rule: "{{ proxysql_query_rule.meta }}"
    mode: get_rule
  register: prule

- name: get user default hostgroup
  get_proxtsql:
    mha_setting: "{{ mha.meta }}"
    proxysql_group: "{{ proxysql_group.meta }}"
    mode: get_user_default_hostgroup
  register: proxysql_dh
'''
