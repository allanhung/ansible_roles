#!/bin/python

import os
import sys
import time
import logging
from optparse import OptionParser
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor

PROXYSQL_CONNECT_TIMEOUT = 20
PROXYSQL_ONLINE = 'ONLINE'
PROXYSQL_OFFLINE_SOFT = 'OFFLINE_SOFT'
PROXYSQL_OFFLINE_HARD = 'OFFLINE_HARD'
REPLICATION_DELAY = 2000
LOG = logging.getLogger(__name__)

class ProxySQL(object):
    """
    ProxySQL describes a single ProxySQL instance.
    :param host: ProxySQL hostname.
    :param port: Port on which ProxySQL listens to admin connections.
    :param user: ProxySQL admin user.
    :param password: Password for ProxySQL admin.
    :param socket: Socket to connect to ProxySQL admin interface.
    """
    def __init__(self, host='localhost', port=6032, user='root', password=None, socket=None):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.socket = socket

    def ping(self):
        """Check health of ProxySQL.
        :return: True if ProxySQL healthy and False otherwise.
        :rtype: bool"""
        try:
            result = self.execute('SELECT 1 AS result')
            return result[0]['result'] == '1'
        except pymysql.err.OperationalError:
            LOG.debug('ProxySQL %s:%d is dead', self.host, self.port)
            return False

    def execute(self, query, *args):
        """Execute query in ProxySQL.
        :param query: Query to execute.
        :type query: str
        :return: Query result or None if the query is not supposed
            to return result
        :rtype: dict
        """
        with self._connect() as conn:
            if not query.lower().startswith('select'):
                LOG.info('execute query: '+query)
            return execute(conn, query, *args)

    def delete_server_from_writer_group(self, server):
        LOG.info('delete mysql host %s from writer group' % (server))
        self.execute("delete from mysql_servers where hostname='%s' and hostgroup_id in (select writer_hostgroup from mysql_replication_hostgroups where writer_hostgroup=mysql_servers.hostgroup_id)" % (server))

    def wait_runtime_status_change(self, server):
        qry = "select count(*) as count from runtime_mysql_servers where hostname = '%s' and status <> '%s'" % (server, PROXYSQL_ONLINE)
        Runtime_ServerStatus=self.execute(qry)
        while int(Runtime_ServerStatus[0]['count']) == 0:
            LOG.info('wait for %s runtime status change!' % (server))
            time.sleep(1)
            Runtime_ServerStatus=self.execute(qry)

    def set_server_status(self, server, status):
        LOG.info('set mysql host %s to %s' % (server, status))
        self.execute("update mysql_servers set status = '%s' where hostname = '%s'" % (status, server))

    def reload_runtime(self):
        """Reload the ProxySQL runtime configuration."""
        LOG.info('LOAD MYSQL SERVERS TO RUNTIME')
        self.execute('LOAD MYSQL SERVERS TO RUNTIME')

    @contextmanager
    def _connect(self):
        """Connect to ProxySQL admin interface."""
        if self.socket is not None:
            conn = pymysql.connect(unix_socket=self.socket,
                                   user=self.user,
                                   passwd=self.password,
                                   connect_timeout=PROXYSQL_CONNECT_TIMEOUT,
                                   cursorclass=DictCursor)
        else:
            conn = pymysql.connect(host=self.host, port=self.port,
                                   user=self.user, passwd=self.password,
                                   connect_timeout=PROXYSQL_CONNECT_TIMEOUT,
                                   cursorclass=DictCursor)

        yield conn
        conn.close()

class MySQLNode(object):
    """
    :param host: hostname of the node.
    :param port: port to connect to.
    :param user: MySQL username to connect to the node.
    :param password: MySQL password.
    """

    def __init__(self, host, port=3306, user='root', password=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def execute(self, query, *args):
        """Execute query in Galera Node.

        :param query: Query to execute.
        :type query: str
        :return: Query result or None if the query is not supposed
            to return result.
        :rtype: dict
        """
        with self._connect() as conn:
            return execute(conn, query, *args)

    def ping(self):
        """Check health of MySQL.
        :return: True if MySQL healthy and False otherwise.
        :rtype: bool"""
        try:
            result = self.execute('SELECT 1 AS result')
            return result[0]['result'] == 1
        except pymysql.err.OperationalError:
            LOG.debug('MySQL %s:%d is dead', self.host, self.port)
            return False

    @property
    def slave_status(self):
        """Return value of a variable from SHOW GLOBAL STATUS"""
        result={}
        sql_result = self.execute('SHOW SLAVE STATUS')
        if sql_result:
            sbm = sql_result[0]["Seconds_Behind_Master"]
            sql_running = (sql_result[0]["Slave_SQL_Running"] == "Yes")
            io_running = (sql_result[0]["Slave_IO_Running"] == "Yes")
            result['offline'] = not (sql_running and io_running and sbm < REPLICATION_DELAY)
            result['seconds_behind_master'] = sbm
            result['slave_sql_running'] = sql_running
            result['slave_io_running'] = io_running
        return result

    @contextmanager
    def _connect(self):
        """Connect to Galera node

        :return: MySQL connection to the Galera node
        :rtype: Connection
        """
        connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            passwd=self.password,
            cursorclass=DictCursor
        )
        yield connection
        connection.close()

def execute(conn, query, *args):
    """Execute query in connection"""
    cursor = conn.cursor()
    cursor.execute(query, *args)
    return cursor.fetchall()

def setup_logging(logger, logfile, debug=False):     # pragma: no cover
    """Configure logging"""

    fmt_str = "%(asctime)s: %(levelname)s: %(module)s.%(funcName)s():%(lineno)d: %(message)s"
    if logfile:
        my_handler = logging.FileHandler(logfile)
    else:
        my_handler = logging.StreamHandler()
    my_handler.setFormatter(logging.Formatter(fmt_str))
    logger.handlers = []
    logger.addHandler(my_handler)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def main():
    # parse comand line arguments
    parser = OptionParser()
    parser.add_option('--host', type='string', default='localhost')
    parser.add_option('--port', type='int', default=6032)
    parser.add_option('--proxysql_user', type='string', default='root')
    parser.add_option('--proxysql_password', type='string', default=None)
    parser.add_option('--mysql_user', type='string', default='monitor')
    parser.add_option('--mysql_password', type='string', default=None)
    parser.add_option('--socket', type='string', default=None)
    parser.add_option('--logfile', type='string', default=None)
    parser.add_option('--debug', action="store_true", dest="debug", default=False)

    (options, args) = parser.parse_args()
    setup_logging(LOG, options.logfile, debug=options.debug)

    pid = str(os.getpid())
    pidfile = "/tmp/check_mysql.pid"
    if os.path.isfile(pidfile):
        LOG.info("%s already exists, exiting" % pidfile)
        sys.exit()

    file(pidfile, 'w').write(pid)
    try:
        changed=False
        PSQL=ProxySQL(options.host, options.port, options.proxysql_user, options.proxysql_password, options.socket)
        # process offline server
        offline_list=PSQL.execute("select distinct hostname from mysql_servers where status like 'OFFLINE%'")
        for host in offline_list:
            MyNode=MySQLNode(host['hostname'],user=options.mysql_user,password=options.mysql_password)
            if MyNode.ping():
                slave_status = MyNode.slave_status
                if slave_status:
                    if (not slave_status['offline']):
                        PSQL.set_server_status(host['hostname'], PROXYSQL_ONLINE)
                        changed=True
                else:
                    PSQL.set_server_status(host['hostname'], PROXYSQL_ONLINE)
                    changed=True
        # process online server
        online_list=PSQL.execute("select distinct hostname from mysql_servers where status = '%s'" % PROXYSQL_ONLINE)
        for host in online_list:
            MyNode=MySQLNode(host['hostname'],user=options.mysql_user,password=options.mysql_password)
            if MyNode.ping():
                slave_status = MyNode.slave_status
                if slave_status and slave_status['offline']:
                    PSQL.wait_runtime_status_change(host['hostname'])            
                    PSQL.set_server_status(host['hostname'], PROXYSQL_OFFLINE_SOFT)
                    changed=True
            else:
                LOG.info('mysql ping failed: %s' % (host['hostname']))
                PSQL.wait_runtime_status_change(host['hostname'])            
                PSQL.delete_server_from_writer_group(host['hostname'])
                PSQL.set_server_status(host['hostname'], PROXYSQL_OFFLINE_HARD)
                changed=True  
        if changed:            
            PSQL.reload_runtime()
            time.sleep(10)
    finally:
        os.unlink(pidfile)

if __name__ == "__main__":
    main()
