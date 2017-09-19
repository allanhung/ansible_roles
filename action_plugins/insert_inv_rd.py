from ansible.plugins.action import ActionBase
from dbinv import dbinv

def insert_inv(options, inv_hosts):
    oraDB = dbinv.OracleDB(options['host'], options['user'], options['pass'], options['port'], options['sid'])
    oraDB.connect()
    for k, v in inv_hosts.items():
        for host in v:
            rows = oraDB.execute("select * from configmg.item_database where host_name = ('{}')".format(host['hostname']))
            if len(rows) == 0:
                column=[]
                value=[]
                column.append('SEQ_NO')
                value.append("ITEM_DATABASE_PK.nextval")
                column.append('SERVICE_NAME')
                value.append("'{}'".format(k))
                column.append('DATA_CENTER')
                value.append("'{}'".format(host['hostname'].split('.')[1].upper()))
                column.append('DB_BRAND')
                value.append("'{}'".format('RD Controlled'))
                column.append('ENVIRONMENT')
                if '-p-' in host['hostname']:
                    value.append("'{}'".format('Production'))
                elif '-s-' in host['hostname']:
                    value.append("'{}'".format('Staging'))
                elif '-b-' in host['hostname']:
                    value.append("'{}'".format('Beta'))
                else:
                    value.append("'{}'".format('Production'))
                column.append('HOST_NAME')
                value.append("'{}'".format(host['hostname']))
                column.append('IP_PHYSICAL_1')
                value.append("'{}'".format(host['ip']))
                column.append('IP_PHYSICAL_2')
                value.append("'{}'".format('ESX'))
                column.append('HARDWARE_TYPE')
                value.append("'{}'".format('VM'))
                ins_sql = "insert into configmg.item_database ({}) values ({})".format(",".join(column), ",".join(value))
                print(ins_sql)
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
        inv_hosts = pillar['inv_hosts']
        options = pillar['dba_inv']
        insert_inv(options, inv_hosts)

        result['failed'] = False
        result['changed'] = False
        return result
