from ansible.plugins.action import ActionBase

def get_mysql_base_user(mysql_user):
    result = []
    for k, v in mysql_user.items():
        if k in ['monitor', 'orch', 'replication']:
            result.extend(v)
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
        mysql_user = pillar['mysql_user']
        facts['mysql_base_user']=get_mysql_base_user(mysql_user)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
