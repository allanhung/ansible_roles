from ansible.plugins.action import ActionBase

def get_group(mha_setting, proxysql_group):
    result={}
    for group_name in mha_setting['group_list']:
        result[group_name]=proxysql_group[group_name] if group_name in proxysql_group.keys() else proxysql_group['default']
    return result

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
        proxysql_group = pillar['proxysql_group']
        facts['proxysql_replication_group']=get_group(mha_setting, proxysql_group)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
