from ansible.plugins.action import ActionBase

def get_mha_conf(myhost, mha_common, mha_setting, mha_user, mysql_common, mysql_repl_user):
    result={}
    for group_name in mha_setting['group_list']:
        conf=[]
        conf.append('[server default]');
        conf.append('ssh_user='+mha_common['ssh_user'])
        conf.append('user='+mha_user['name'])
        conf.append('password='+mha_user['password'])
        conf.append('repl_user='+mysql_repl_user['name'])
        conf.append('repl_password='+mysql_repl_user['password'])
        conf.append('master_binlog_dir='+mysql_common['datadir'])
        conf.append('master_ip_failover_script='+mha_common['script_dir']+'/master_ip_failover')
        conf.append('master_ip_online_change_script='+mha_common['script_dir']+'/master_ip_online_change')
        conf.append('manager_workdir='+mha_common['log_dir']+'/'+group_name)
        conf.append('manager_log='+mha_common['log_dir']+'/'+group_name+'/manager.log')
        conf.append('remote_workdir='+mha_common['log_dir']+'/'+group_name)
        conf.append('secondary_check_script=masterha_secondary_check -s '+' -s '.join(mha_setting['slave_list'][group_name])+' ping_interval=3')
        conf.append('report_script='+mha_common['script_dir']+'/mha_send_report')
        conf.append('')
        tmp_conf=[]
        for i, n in enumerate(mha_setting['mha_node_list'][group_name]):
            node_conf=[]
            node_conf.append('[server'+str(i+1)+']')
            node_conf.append('hostname='+n['hostname'])
            for m in n['mha_args']:
                for x, y in m.items():
                    node_conf.append(x+'='+y)
            tmp_conf.append('\n'.join(node_conf))
        conf.append('\n\n'.join(tmp_conf))
        result[group_name]={'context': '\n'.join(conf)}
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
        mha_common = pillar['mha_common']
        mha_setting = pillar['mha_setting']
        mysql_common = pillar['mysql_common']
        mha_user = pillar['mysql_user']['mha'][0]
        mysql_repl_user = pillar['mysql_user']['replication'][0]

        facts['mha_conf'] = get_mha_conf(myhost, mha_common, mha_setting, mha_user, mysql_common, mysql_repl_user)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
