from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        facts = {}
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if result.get('skipped'):
            return result

        ssh_config_key = self._task.args.get('ssh_config_key', 'ssh_config')
        pillar = task_vars.get('pillar', {})
        ssh_config = pillar.get(ssh_config_key, {})
        ssh_config_result = []
        tmp_cnf=[]
        for k, v in ssh_config.items():
            tmp_cnf.append('Host '+str(k))
            for m, n in v.items():
                if isinstance(n, list):
                    for x in n:
                        tmp_cnf.append('    '+m+' '+str(x))
                else:
                    tmp_cnf.append('    '+m+' '+str(n))
            ssh_config_result.append('\n'.join(tmp_cnf))
        facts[ssh_config_key]='\n'.join(ssh_config_result)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
