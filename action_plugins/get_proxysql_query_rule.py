from ansible.plugins.action import ActionBase

def get_rule(proxysql_replication_group, proxysql_query_rule):
    result={}
    for k, v in proxysql_replication_group.items():
        for m, n in proxysql_query_rule.items():
            result[k+"_"+m]={}
            result[k+"_"+m]['group_name']=k
            result[k+"_"+m]['rule_id']=m
            result[k+"_"+m]['active']=n['active']
            result[k+"_"+m]['match_pattern']=n['match_pattern']
            result[k+"_"+m]['destination_hostgroup']=v[n['destination_hostgroup']]
            result[k+"_"+m]['apply']=n['apply']
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
        proxysql_replication_group = pillar['proxysql_replication_group']
        proxysql_query_rule = pillar['proxysql_query_rule']
        facts['proxysql_qry_rule']=get_rule(proxysql_replication_group, proxysql_query_rule)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
