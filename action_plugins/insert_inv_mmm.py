from ansible.plugins.action import ActionBase
from dbinv import dbinv

def insert_inv(myhost, options, mmm_group, mmm_setting, hostvars, user, password):
    oraDB = dbinv.OracleDB(options['host'], options['user'], options['pass'], options['port'], options['sid'])
    oraDB.connect()
#    del_sql = "delete configmg.item_database where HOST_NAME like '%p-concad%'"
#    oraDB.execute(del_sql)
    # get_data.py --password TrendAdm2012
    for host in mmm_group[mmm_setting['group_name']]['hosts']:
        rows = oraDB.execute("select * from configmg.item_database where host_name = '{}'".format(host['hostname']))
        if len(rows) == 0:
            column=[]
            value=[]
            column.append('SEQ_NO')
            value.append("ITEM_DATABASE_PK.nextval")
            column.append('SERVICE_NAME')
            value.append("'{}'".format(mmm_setting['group_name'].upper()))
            column.append('DATA_CENTER')
            value.append("'{}'".format(myhost['domain'].upper()))
            column.append('DB_BRAND')
            if 'mm' in host['hostname']:
                value.append("'{}'".format('Not A Database'))
                column.append('DB_VERSION')
                value.append("'{}'".format('Not A Database'))
            else:
                value.append("'{}'".format('MySQL'))
                column.append('DB_VERSION')
                value.append("'{}'".format('MySQL '+mmm_group[mmm_setting['group_name']]['mysql_ver']))
                column.append('DB_EDITION')
                value.append("'{}'".format('Community'))
                column.append('HA_TECHNOLOGY')
                value.append("'{}'".format('Replication 2-Way + MMM'))
                column.append('ZENOSS_TEMPLATE')
                value.append("'{}'".format("[''MySQL''; ''MySQL-Slave''; ''Check_Hardware''; ''Device_HighMemory'']"))
            column.append('SERVICE_PORT')
            value.append("'{}'".format('3306'))
            column.append('HA_PEER_1')
            value.append("'{}'".format(host['ha_peer']))
            column.append('ENVIRONMENT')
            if '-p-' in host['hostname']:
                value.append("'{}'".format('Production'))
            elif '-s-' in host['hostname']:
                value.append("'{}'".format('Staging'))
            elif '-b-' in host['hostname']:
                value.append("'{}'".format('Beta'))
            column.append('HOST_NAME')
            value.append("'{}'".format(host['hostname']))
            column.append('URL_SERVICE_1')
            value.append("'{}'".format(mmm_group[mmm_setting['group_name']]['write_vip'].keys()[0]))
            column.append('URL_SERVICE_2')
            value.append("'{}'".format(mmm_group[mmm_setting['group_name']]['read_vip'].keys()[0]))
            column.append('IP_PHYSICAL_1')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_ssh_host']))
            column.append('IP_PHYSICAL_2')
            value.append("'{}'".format('ESX'))
            column.append('IP_SERVICE_1')
            value.append("'{}'".format(mmm_group[mmm_setting['group_name']]['write_vip'].values()[0][0]))
            column.append('IP_SERVICE_1_ATTR')
            value.append("'{}'".format('VIP(Write Only)'))
            for i, read_ip in enumerate(mmm_group[mmm_setting['group_name']]['read_vip'].values()[0]):
                column.append('IP_SERVICE_'+str(i+2))
                value.append("'{}'".format(read_ip))
                column.append('IP_SERVICE_'+str(i+2)+'_ATTR')
                value.append("'{}'".format('VIP(Read Only)'))
            column.append('OS_TYPE')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_distribution']+' '+hostvars[host['hostname']]['ansible_distribution_major_version']))
            column.append('OS_PATCH_LEVEL')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_distribution']+' '+hostvars[host['hostname']]['ansible_distribution_version']))
            column.append('HARDWARE_TYPE')
            value.append("'{}'".format('VM'))
            column.append('ACCT_READER')
            value.append("'{}'".format(user))
            column.append('ACCT_READER_PASSWD')
            value.append("'{}'".format(password))
            column.append('ACCT_WRITER')
            value.append("'{}'".format(user))
            column.append('ACCT_WRITER_PASSWD')
            value.append("'{}'".format(password))
            ins_sql = "insert into configmg.item_database ({}) values ({})".format(",".join(column), ",".join(value))
            oraDB.execute(ins_sql)
    oraDB.connection.commit()
    oraDB.disconnect()

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
        options = pillar['dba_inv']
        mmm_group = pillar['mmm_group']
        mmm_setting = pillar['mmm_setting']
        mmm_user = pillar['mysql_user']['monitor'][0]['name']
        mmm_password = pillar['mysql_user']['monitor'][0]['password']
        debug = self._task.args.get('debug', False)
        insert_inv(myhost, options, mmm_group, mmm_setting, hostvars, mmm_user, mmm_password)

        result['failed'] = False
        result['changed'] = False
        return result
