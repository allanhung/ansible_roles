from ansible.plugins.action import ActionBase

def get_stage(myhost, stage, hostgroup):
    for k, v in hostgroup.items():
        m = [hostname.lower() for hostname in v]
        if (myhost['hostname']).lower() in m or (myhost['hostname']+'.'+myhost['domain']).lower() in m:
            return stage[k]
            break

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts = {}
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result
        
        role_name = self._task.args.get('role_name', None)
        stage_name = role_name+'_stage'
        pillar = task_vars.get('pillar', {})
        myhost = pillar['myhost']
        hostgroup = pillar['hostgroup']
        stage = pillar[stage_name]

        facts[stage_name+'_by_os'] = get_stage(myhost, stage, hostgroup)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
