from ansible.plugins.action import ActionBase

def get_mmm_setting(myhost, mmm_group, hostvars):
    result={}
    result['hosts']=[]
    result['roles']=[]
    result['heartbeat']={}
    result['group_name']=''
    result['mmm_role']=''
    result['mmm_host']=''
    ha_host_list=[]
    writer_host_list=[]
    writer_ip_list=[]
    reader_host_list=[]
    reader_host_ip_list=[]
    reader_ip_list=[]

    for k, v in mmm_group.items():
        for m in v['hosts']:
            if myhost['hostname']+'.'+myhost['domain'] ==  m['hostname']:
                result['group_name']=k
                result['mmm_role']=m['role']
                if 'mmm_host' in m.keys():
                    result['mmm_host']=m['mmm_host']
                result['monitor_vip']=v['monitor_vip'].values()[0][0]
                break
    for k, v in mmm_group[result['group_name']].items():
        if k == 'write_vip':
            for m, n in v.items():
                writer_ip_list.extend(n)
        if k == 'read_vip':
            for m, n in v.items():
                reader_ip_list.extend(n)
        if k == 'hosts':
            for m in v:
                if m['role'] == 'monitor':
                    if myhost['hostname']+'.'+myhost['domain'] == m['hostname']:
                        result['heartbeat']['ucast'] = hostvars[m['ha_peer']]['ansible_ssh_host']
                    ha_host_list.append(m['hostname'])
                else:
                    host={}
                    host['name']='mmm_'+m['mmm_host']
                    host['ip']=hostvars[m['hostname']]['ansible_ssh_host']
                    host['mode']=m['role']
                    if m['role'] == 'master':
                        writer_host_list.append(host['name'])
                        reader_host_list.append(host['name'])
                        reader_host_ip_list.append(host['ip'])
                    elif m['role'] == 'slave':
                        reader_host_list.append(host['name'])
                        reader_host_ip_list.append(host['ip'])
                    if 'peer' in m.keys():
                        host['peer']='mmm_'+m['peer']
                    result['hosts'].append(host)
    result['heartbeat']['ha_nodes']=ha_host_list
    result['roles'].append({'name': 'writer', 'hosts': ', '.join(writer_host_list), 'ips': ', '.join(writer_ip_list), 'mode': 'exclusive'})
    result['roles'].append({'name': 'reader', 'hosts': ', '.join(reader_host_list), 'ips': ', '.join(reader_ip_list), 'mode': 'balanced'})
    result['reader_host_ip']=', '.join(reader_host_ip_list)
    return result

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
        mmm_group = pillar['mmm_group']

        facts['mmm_setting'] = get_mmm_setting(myhost, mmm_group, hostvars)

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
