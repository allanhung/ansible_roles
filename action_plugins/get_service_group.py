from ansible.plugins.action import ActionBase

def get_service_group(myhost, hostgroup):
    for k, v in hostgroup.items():
        m = [hostname.lower() for hostname in v]
        if (myhost['hostname']).lower() in m or (myhost['hostname']+'.'+myhost['domain']).lower() in m:
            return k
            break

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
        hostgroup = pillar['hostgroup']

        facts['service_group'] = get_service_group(myhost, hostgroup)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
