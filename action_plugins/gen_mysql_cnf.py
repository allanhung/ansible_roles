from ansible.plugins.action import ActionBase

def get_mycnf(myhost, ip, cpucount, memory, mysql_daemon, mysql_common, config, config_by_version, mysql_version):
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
        datadir: /data/mysql
        error_log: mysql.err
        pid_file: mysqld.pid
        socket: mysql.sock
        software_dir: /opt/software/mysql
        slow_log: mysql-slow.log
        port:
          - 3306

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
    """
    multi_instance=(len(mysql_common['port']) > 1)
    server_id=ip.replace(".","")
    my_cnf=[]
    datadir_list=[]
    service_list=[]
    socket_list=[]
    service_cnf=[]
    hostport_socket={}

    for port in mysql_common['port']:
        port=str(port)
        datadir=mysql_common['datadir']+'_'+port if multi_instance else mysql_common['datadir']
        datadir_list.append(datadir)
        service=mysql_daemon['mysql_daemon']+'@'+port if multi_instance else mysql_daemon['mysql_daemon']
        service_list.append(service)
        socket=datadir+'/'+mysql_common['socket']
        socket_list.append(socket)
        if not multi_instance:
            hostport_socket[myhost['hostname']]=socket
        hostport_socket[myhost['hostname']+'@'+port]=socket
        blocktitle='mysqld@'+port if multi_instance else 'mysqld'

        my_cnf.append('['+blocktitle+']')
        tmp_cnf=[]
        tmp_cnf.append('port='+port)
        tmp_cnf.append('datadir='+datadir)
        tmp_cnf.append('log_error='+datadir+'/'+mysql_common['error_log'])
        tmp_cnf.append('server_id='+server_id)
       
        if '5.7.' in mysql_version:
           config.update(config_by_version['5.7'])
        elif '5.6.' in mysql_version:
           config.update(config_by_version['5.6'])

        for k, v in config.items():
            if isinstance(v, list):
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
                    if memory <= 16384:
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
        if multi_instance:
            service_cnf.append({'filename': 'my_'+port+'.cnf', 'file_context' :'\n'.join(['[mysqld]']+sorted(tmp_cnf))})
        my_cnf.append('')

    port=str(mysql_common['port'][0])
    datadir=mysql_common['datadir']+'_'+port if multi_instance else mysql_common['datadir']
    my_cnf.append('[client]')
    my_cnf.append('port='+port)
    my_cnf.append('socket='+datadir+'/'+mysql_common['socket'])
    return '\n'.join(my_cnf), service_list, datadir_list, socket_list, multi_instance, service_cnf, hostport_socket

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
        daemon = pillar['mysql_daemon']
        common = pillar['mysql_common']
        config = pillar['mysql_config']
        config_by_version = pillar['mysql_config_by_version']
        ip = task_vars['ansible_ssh_host']
        cpucount = task_vars['ansible_processor_vcpus']
        memory = task_vars['ansible_memtotal_mb']
        mysql_version = self._task.args.get('mysql_version', '')
        my_cnf, service_list, datadir_list, socket_list, multi, service_cnf, hostport_socket = get_mycnf(myhost, ip, cpucount, memory, daemon, common, config, config_by_version, mysql_version)
        facts['mysql_cnf']={'my_cnf': my_cnf, 'service_list': service_list, 'datadir_list': datadir_list, 'socket_list': socket_list, 'multi_instance': multi, 'service_cnf': service_cnf, 'hostport_socket': hostport_socket}

        result['failed'] = False
        pillar.update(facts)
        result['ansible_facts']={'pillar': pillar}
        result['changed'] = False
        return result
