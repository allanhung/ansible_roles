from ansible.plugins.action import ActionBase

def get_mysql_main_version(mysql_version):
    if mysql_version:
        (a_ver, b_ver, c_ver) = mysql_version.split(".",2)
        return a_ver+'.'+b_ver
    else:
        return ''

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
        mysql_version = self._task.args.get('mysql_version', '')
        mysql_main_version = get_mysql_main_version(mysql_version)
        facts['mysql_version']={'main': str(mysql_main_version), 'full': str(mysql_version)}

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
