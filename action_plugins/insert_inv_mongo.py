from ansible.plugins.action import ActionBase
from dbinv import dbinv

def insert_inv(myhost, options, mongo_replica, hostvars, user):
    oraDB = dbinv.OracleDB(options['host'], options['user'], options['pass'], options['port'], options['sid'])
    oraDB.connect()
    del_sql = "delete configmg.item_database where HOST_NAME like '%tmdk-p-%'"
    oraDB.execute(del_sql)
    for host in mongo_replica['RS1']:
        rows = oraDB.execute("select * from configmg.item_database where host_name = '{}'".format(host['hostname']))
        if len(rows) == 0:
            column=[]
            value=[]
            column.append('SEQ_NO')
            value.append("ITEM_DATABASE_PK.nextval")
            column.append('SERVICE_NAME')
            value.append("'{}'".format(((host['hostname']).split('-')[0]).upper()))
            column.append('DATA_CENTER')
            value.append("'{}'".format(myhost['domain'].upper()))            
            column.append('DB_BRAND')
            value.append("'{}'".format('NoSQL MongoDB'))
            column.append('DB_VERSION')
            value.append("'{}'".format('MongoDB 4.0.1'))
            column.append('DB_EDITION')
            value.append("'{}'".format('Community'))
            column.append('HA_TECHNOLOGY')
            value.append("'{}'".format('Replica Set'))
            column.append('SERVICE_PORT')
            value.append("'{}'".format('27017'))
            column.append('ENVIRONMENT')
            if '-p-' in host['hostname']:
                value.append("'{}'".format('Production'))
            elif '-s-' in host['hostname']:
                value.append("'{}'".format('Staging'))
            elif '-b-' in host['hostname']:
                value.append("'{}'".format('Beta'))
            column.append('HOST_NAME')
            value.append("'{}'".format(host['hostname']))
            column.append('IP_PHYSICAL_1')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_ssh_host']))
            column.append('IP_SERVICE_1')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_ssh_host']))
            column.append('OS_TYPE')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_distribution']+' '+hostvars[host['hostname']]['ansible_distribution_major_version']))
            column.append('OS_PATCH_LEVEL')
            value.append("'{}'".format(hostvars[host['hostname']]['ansible_distribution']+' '+hostvars[host['hostname']]['ansible_distribution_version']))
            column.append('HARDWARE_TYPE')
            value.append("'{}'".format('VM'))
            column.append('ACCT_READER')
            value.append("'{}'".format(user[2]['name']))
            column.append('ACCT_READER_PASSWD')
            value.append("'{}'".format(user[2]['password']))
            column.append('ACCT_WRITER')
            value.append("'{}'".format(user[0]['name']))
            column.append('ACCT_WRITER_PASSWD')
            value.append("'{}'".format(user[0]['password']))
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
        mongo_replica = pillar['mongo_replica']
        mongo_user = pillar['mongo_user']
        debug = self._task.args.get('debug', False)
        insert_inv(myhost, options, mongo_replica, hostvars, mongo_user)

        result['failed'] = False
        result['changed'] = False
        return result
