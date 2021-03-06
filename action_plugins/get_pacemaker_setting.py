from ansible.plugins.action import ActionBase

def get_setting(myhost, pacemaker_group, hostvars):
    result={}
    ms=[]
    for k, v in pacemaker_group.items():
        if myhost['hostname'] in v['nodes'] or myhost['hostname']+'.'+myhost['domain'] in v['nodes']:
            result['cluster_name']=k
            result['property']=v['property']
            result['resource']=v['resource']
            result['nodes']=[]
            for node in v['nodes']:
                result['nodes'].append(hostvars[node]['ansible_ssh_host'])
            for r in v['resource']:
                if r['type'].split(':')[0] == 'systemd':
                    ms.append(r['type'].split(':')[1])
    return result, ms

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts = {}
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result
        
        hostvars = task_vars.get('hostvars', {})
        pillar = task_vars.get('pillar', {})
        myhost = pillar['myhost']
        pacemaker_group = pillar['pacemaker_group']
        facts['pacemaker_setting'], facts['pacemaker_manage_service']=get_setting(myhost, pacemaker_group, hostvars)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
