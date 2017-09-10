from ansible.plugins.action import ActionBase
from pypillar.utils import *

def get_replication(master_hostvars, master_setting, repl_user):
    myhost = get_host.parser_host(master_hostvars['inventory_hostname'], master_hostvars['ansible_distribution'], master_hostvars['ansible_distribution_version'])
    master_setting['master_ansible_host']=master_setting['master_host']
    master_setting['master_host']=myhost['hostname']
    master_setting['master_ip']=master_hostvars['ansible_ssh_host']
    master_setting['master_port']=str(v['master_port']) if 'master_port' in  master_setting.keys() else '3306'
    if  'mode' in master_setting.keys() and master_setting['mode'].lower() == 'gtid':
        master_setting['master_auto_position']='1'
    master_setting['master_user']=repl_user['name']
    master_setting['master_password']=repl_user['password']
    return master_setting

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts={}
        if task_vars is None:
            task_vars = dict()
 
        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result

        hostvars = task_vars.get('hostvars',{})
        pillar = task_vars.get('pillar', {})
        master_setting = pillar.get('mysql_replication', {})
        master_hostvars = hostvars[master_setting['master_host']]
        repl_user = pillar['mysql_user']['replication'][0]
        facts['mysql_replication']=get_replication(master_hostvars, master_setting, repl_user)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
