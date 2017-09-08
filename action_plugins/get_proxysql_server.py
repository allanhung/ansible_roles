from ansible.plugins.action import ActionBase

def get_server(mha_setting, proxysql_group):
    result={}
    for group_name in mha_setting['group_list']:
        dict_index=0
        for i, host in enumerate(mha_setting['mha_node_list'][group_name]):
            result[i+dict_index]={}
            result[i+dict_index]['hostname']=host['hostname']
            result[i+dict_index]['group_name']=group_name
            result[i+dict_index]['group_id']=proxysql_group[group_name]['write'] if group_name in proxysql_group.keys() else proxysql_group['default']['write']
            # add msater to read group
            if host['role'].lower() == 'master':
                dict_index+=1
                result[i+dict_index]={}
                result[i+dict_index]['hostname']=host['hostname']
                result[i+dict_index]['group_name']=group_name
                result[i+dict_index]['group_id']=proxysql_group[group_name]['read'] if group_name in proxysql_group.keys() else proxysql_group['default']['read']
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
        facts['proxysql_server']=get_server(mha_setting, proxysql_group)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
