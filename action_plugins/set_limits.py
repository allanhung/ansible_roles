from ansible.plugins.action import ActionBase

"""
mysql:
  nofile: 65535
  nproc: 15000

- {name: 'mysql', type: 'soft', item: 'nofile', value: 65535}
- {name: 'mysql', type: 'hard', item: 'nofile', value: 65535}
- {name: 'mysql', type: 'soft', item: 'nproc', value: 15000}
- {name: 'mysql', type: 'hard', item: 'nproc', value: 15000}
"""

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts={}
        if task_vars is None:
            task_vars = dict()
 
        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result

        limits_key = self._task.args.get('limits_key', 'root_limits')
        pillar = task_vars.get('pillar', {})
        limits_conf = pillar.get(limits_key, {})
        limits_result = []
        for k,v in limits_conf.items():
            for m, n in v.items():
                limits_result.append({'name': k, 'type': 'soft', 'item': m, 'value': n})
                limits_result.append({'name': k, 'type': 'hard', 'item': m, 'value': n})
        facts[limits_key]=limits_result

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
