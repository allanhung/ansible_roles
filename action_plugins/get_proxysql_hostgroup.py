from ansible.plugins.action import ActionBase

def get_user_default_hostgroup(mha_setting, proxysql_replication_group):
    result=[]
    hostgroup=proxysql_replication_group[mha_setting['group_list'][0]]['write']
    return hostgroup

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts = {}
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result
        
        pillar = task_vars.get('pillar', {})
        myhost = pillar['myhost']
        mha_setting = pillar['mha_setting']
        proxysql_replication_group = pillar['proxysql_replication_group']
        facts['proxysql_hostgroup']=get_user_default_hostgroup(mha_setting, proxysql_replication_group)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
