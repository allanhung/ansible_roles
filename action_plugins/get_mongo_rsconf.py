from ansible.plugins.action import ActionBase

def get_mongo_rsconf(myhost, mongo_replica):
    result={}
    for rs_name, member_list in mongo_replica.items():
        for member in member_list:
            if member['hostname'] == myhost['hostname']+'.'+myhost['domain']:
                result['rs_name'] = rs_name
                result['hostname'] = member['hostname']
                result['role'] = member['role']
                break
    result['members']=[]
    for member in mongo_replica[result['rs_name']]:
        if member['hostname'] != myhost['hostname']+'.'+myhost['domain']:
            result['members'].append({'hostname': member['hostname'], 'role': member['role']})
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
        hostvars = task_vars.get('hostvars', {})
        myhost = pillar['myhost']
        mongo_replica = pillar['mongo_replica']

        facts['mongo_rsconf'] = get_mongo_rsconf(myhost, mongo_replica)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
