#!/bin/python

from ansible.plugins.action import ActionBase

def get_lvs_pxc_config(pillar, hostvars):
    lvs_config=[]
    lvs_vip=''
    if 'lvs_group' in pillar.keys() and 'pxcluster' in pillar['lvs_group'].keys():
        lvs_config.append('# Virtual Server for pxc cluster')
        lvs_vip=pillar['lvs_group']['pxcluster']['vip']
        lvs_config.append('virtual={}:{}'.format(lvs_vip, pillar['lvs_group']['pxcluster']['listen_port']))
        for node in pillar['lvs_group']['pxcluster']['nodes']:
            lvs_config.append("\treal={}:{} gate 50".format(hostvars[node]['ansible_ssh_host'], pillar['lvs_group']['pxcluster']['listen_port']))
        for k, v in pillar['lvs_group']['pxcluster'].items():
            if k not in ['vip', 'listen_port', 'nodes']:
                lvs_config.append("\t{}={}".format(k, v))
    return '\n'.join(lvs_config), lvs_vip

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
        lvs_pxc_config, lvs_vip = get_lvs_pxc_config(pillar, hostvars)
        facts['lvs_config']=lvs_pxc_config
        facts['lvs_vip']=lvs_vip

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
