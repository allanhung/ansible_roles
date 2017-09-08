from ansible.plugins.action import ActionBase

def get_mha_setting(myhost, mha_group, mha_common):
    result={}
    result['all_server_list']=[]
    result['server_list']={}
    result['mha_node_list']={}
    result['slave_list']={}
    group_list=[]
    role=''
    for k, v in mha_group.items():
        for i, m in reversed(list(enumerate(v))):
            if myhost['hostname']+'.'+myhost['domain'] ==  m['hostname']:
                group_list.append(k)
                role=m['role'].lower()
    if group_list:
        for group_name in group_list:
            server_list=[]
            mha_node_list=[]
            slave_list=[]
            for n in mha_group[group_name]:
                server_list.append(n['hostname'])
                if n['role'].lower() <> 'monitor':
                    mha_node_list.append({'hostname': n['hostname'], 'mha_args': n['mha_args'], 'role': n['role']})
                if n['role'].lower() == 'slave':
                    slave_list.append(n['hostname'])
            result['all_server_list'].extend(server_list)
            result['server_list'][group_name]=server_list
            result['mha_node_list'][group_name]=mha_node_list
            result['slave_list'][group_name]=slave_list
    result['group_list'] = group_list
    result['all_server_list']=list(set(result['all_server_list']))
    result['is_mha']=(group_list is not None)
    result['role']=role
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
        mha_group = pillar['mha_group']
        mha_common = pillar['mha_common']

        facts['mha_setting'] = get_mha_setting(myhost, mha_group, mha_common)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
