from ansible.plugins.action import ActionBase

def get_setting(myhost, pacemaker_group):
    result={}
    for k, v in pacemaker_group.items():
        if myhost['hostname'] in v['nodes'].keys() or myhost['hostname']+'.'+myhost['domain'] in v['nodes'].keys():
            result['cluster_name']=k
            result['property']=v['property']
            result['resource']=v['resource']
            result['nodes']=v['nodes'].values()
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
        pacemaker_group = pillar['pacemaker_group']
        facts['pacemaker_setting']=get_setting(myhost, pacemaker_group)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
