#!/bin/python

from ansible.plugins.action import ActionBase

def get_pxc_node(pillar, hostvars):
    cluster_ip_list=[]
    cluster_db_vip=''
    if 'pxc_group' in pillar.keys() and 'pxcluster' in pillar['pxc_group'].keys():
        for node in pillar['pxc_group']['pxcluster']:
            if 'vip' in node.keys():
                cluster_ip_list.append(node['vip'])
                cluster_db_vip=node['vip']
            else:
                cluster_ip_list.append(hostvars[node['hostname']]['ansible_ssh_host'])
        cluster_ip_list=list(set(cluster_ip_list))
    return cluster_ip_list, cluster_db_vip

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts = {}
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result
        
        pillar = task_vars.get('pillar', {})
        hostvars = task_vars.get('hostvars', {})
        pxc_node_list, pxc_db_vip = get_pxc_node(pillar, hostvars)
        facts['pxc_node_list']=pxc_node_list
        facts['pxc_db_vip']=pxc_db_vip

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
