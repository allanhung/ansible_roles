#!/bin/python

from __future__ import (absolute_import, division, print_function)
from ansible.plugins.action import ActionBase
from copy import deepcopy

def get_mycnf(pillar, hostvars, myhost, ip, cpucount, memory, mysql_daemon, mysql_common, config, config_by_version, config_by_plugin, mysql_version, with_plugin):
    """
    mysql_daemon:
      default:
        6:
          mysql_daemon: mysql
        7:
          mysql_daemon: mysqld

    mysql_common:
      default:
        config_file: /etc/my.cnf
        data_dir: /data/mysql
        error_log: mysql.err
        pid_file: mysqld.pid
        socket: mysql.sock
        software_dir: /opt/software/mysql
        slow_log: mysql-slow.log
        port: 3306

    mysql_config:
      default:
        mysqld:
          binlog_cache_size: "524288"
          binlog_format: row
          event_scheduler : "1"
          innodb_autoextend_increment: "10"
          innodb_log_file_size : my_memory*0.02
          innodb_monitor_enable: 
            - '"module_adaptive_hash"'
            - '"module_buffer"'
          innodb_read_io_threads: my_vcpu_count
          innodb_undo_directory: my_datadir

    mysql_config_by_version:
      default:
        "5.7": 
          default_password_lifetime : 0
          innodb_undo_log_truncate: 1
          
    mysql_config_by_plugin:
      default:
        audit:
          plugin-load: AUDIT=libaudit_plugin.so
          audit_json_file: 1
          audit_json_file_sync: 100
          audit_record_cmds: alter,drop,truncate,rename,create,grant
          audit_uninstall_plugin: 1
        validate_password:
          plugin-load-add: validate_password.so
          validate_password_length: 8
          validate_password_mixed_case_count: 1
          validate_password_number_count: 1
          validate_password_policy: 1
          validate_password_special_char_count: 1
    """
    server_id=ip.replace(".","")
    my_cnf=[]
    hostport_socket={}

    port=str(mysql_common['port'])
    datadir=mysql_common['data_dir']
    service=mysql_daemon['mysql_daemon']
    socket=mysql_common['socket']

    my_cnf.append('[mysqld]')
    tmp_cnf=[]
    tmp_cnf.append('port='+port)
    tmp_cnf.append('datadir='+datadir)
    tmp_cnf.append('log_error='+datadir+'/'+mysql_common['error_log'])
    tmp_cnf.append('server_id='+server_id)
    tmp_cnf.append('report_host='+ip)
   
    config.update(config_by_version[eval(mysql_version['main'])])

    if with_plugin:
        for k, v in config_by_plugin.items():
            if k in with_plugin:
                for m, n in v.items():
                    if m in config.keys():
                        config[m].update(n)
                    else:
                        config[m]=n
                if k == 'wsrep':
                    cluster_ip_list = []
                    for node in pillar['pxc_group']['pxcluster']:
                        if 'vip' in node.keys():
                            cluster_ip_list.append(node['vip'])
                        else:
                            cluster_ip_list.append(hostvars[node['hostname']]['ansible_ssh_host'])
                        cluster_ip_list=list(set(cluster_ip_list))
                    config['wsrep_cluster_address']='gcomm://'+','.join(cluster_ip_list)
                    config['wsrep_node_address']=ip
                    config['wsrep_node_name']=myhost['hostname']+'.'+myhost['domain']
                    config['wsrep_sst_auth']='{}:{}'.format(pillar['mysql_user']['pxc'][0]['name'],pillar['mysql_user']['pxc'][0]['password'])

    for k, v in config.items():
        if k == 'sql_mode':
            tmp_cnf.append(k+'='+','.join(v))
        elif isinstance(v, list):
            for m in v:
                tmp_cnf.append(k+'='+str(m))
        elif k == 'plugin_load':
            tmp_plugin=[]
            for m, n in v.items():
                tmp_plugin.append(m+'='+n)
            tmp_cnf.append(k+'="'+';'.join(tmp_plugin)+'"')
        else:
            tmp_cnf.append(k+'='+str(v))

    for i, line in enumerate(tmp_cnf):
        line=line.replace('my_vcpu_count', str(cpucount))
        line=line.replace('my_datadir', str(datadir))
        if 'my_memory' in line:
            k, v = line.split('=')
            if k == 'innodb_buffer_pool_size':
                if memory <= 4096:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.4)))+'M'
                elif memory <= 16384:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.5)))+'M'
                elif memory > 16384 and memory <= 24576:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.55)))+'M'
                elif memory > 24576 and memory <= 32768:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.60)))+'M'
                elif memory > 32768 and memory <= 65536:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.65)))+'M'
                elif memory > 65536:
                    line='innodb_buffer_pool_size='+str(abs(int(memory*0.7)))+'M'
            else:
                m, n = v.split('*')
                line=k+'='+str(abs(int(memory*float(m))))+n.replace('my_memory','')
        tmp_cnf[i]=line

    my_cnf.extend(sorted(tmp_cnf))
    my_cnf.append('')

    my_cnf.append('[client]')
    my_cnf.append('port='+port)
    my_cnf.append('socket='+mysql_common['socket'])
    return '\n'.join(my_cnf)

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
        daemon = pillar['mysql_daemon']
        common = pillar['mysql_common']
        config = deepcopy(pillar['mysql_config'])
        config_by_version = pillar['mysql_config_by_version']
        config_by_plugin = pillar['mysql_config_by_plugin']
        ip = task_vars['ansible_ssh_host']
        cpucount = task_vars['ansible_processor_vcpus']
        memory = task_vars['ansible_memtotal_mb']
        mysql_version = self._task.args.get('mysql_version', {})
        with_plugin = self._task.args.get('with_plugin', False)
        my_cnf = get_mycnf(pillar, hostvars, myhost, ip, cpucount, memory, daemon, common, config, config_by_version, config_by_plugin, mysql_version, with_plugin)
        facts['mysql_cnf']={'my_cnf': my_cnf}

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
