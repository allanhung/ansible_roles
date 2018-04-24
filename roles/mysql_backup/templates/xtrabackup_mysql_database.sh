#!/bin/bash
#     Name: xtrabackup_mysql_database.sh
#   Deploy: cd /opt/dba_script; cat /dev/null > xtrabackup_mysql_database.sh; vi xtrabackup_mysql_database.sh
#
#  Purpose: 1. Backup MySQL using Percona Xtrabackup with full or incremental mode.
#
#           2. The backup script also generate two restore scripts in $BACKUP_BASE/daily/control/
#              a. To apply logs and prepare the backup restore_db_1_prepare.sh 
#              b. Copy backup the database restore_db_2_copyback.sh
# 
#           3. To restore and recover database:
#              a. Ensure all the backup files are in its original backup directory.
#              b. Ensure datadir specified in /etc/my.cnf is created and kept empty.
#              c. Go to $BACKUP_BASE/daily/control/
#              d. nohup ./restore_db_1_prepare.sh &
#              e. nohup ./restore_db_2_copyback.sh &
#              f. Go to data directory ( datadir )
#              g. Change owner of all sub-directories and files to mysql
#              h. Start MySQL service
#
#  Deployment:
#              1. Install Percona xtrabackup 2.1
#              
#              2. Create a MySQL table to record backup status.
#                 mysql>
#                        USE mysql;
#                        CREATE TABLE IF NOT EXISTS dba_backup_log 
#                       ( id VARCHAR(20), start_time DATETIME, end_time DATETIME, backup_type VARCHAR(20), backup_file VARCHAR(200),
#                         status VARCHAR(10), size VARCHAR(20), remarks VARCHAR(200) );
#
#              3. Create a MySQL user for backup ( change password )
#                 mysql>
#                        DROP USER dbabackup@'localhost';
#                        CREATE USER dbabackup@'localhost' IDENTIFIED BY 'DonForget2ChangeMe';
#                        GRANT USAGE ON mysql.* TO 'dbabackup'@'localhost';
#                        GRANT LOCK TABLES, SELECT, RELOAD, SUPER, REPLICATION CLIENT, FILE ON *.* TO 'dbabackup'@'localhost';
#                        GRANT ALL ON mysql.dba_backup_log TO 'dbabackup'@'localhost';
#                        DROP USER dbabackup@'%';
#                        CREATE USER dbabackup@'%' IDENTIFIED BY 'DonForget2ChangeMe';
#                        GRANT USAGE ON mysql.* TO 'dbabackup'@'%';
#                        GRANT LOCK TABLES, SELECT, RELOAD, SUPER, REPLICATION CLIENT, FILE ON *.* TO 'dbabackup'@'%';
#                        GRANT ALL ON mysql.dba_backup_log TO 'dbabackup'@'%';
#                        FLUSH PRIVILEGES;
#                        EXIT;
#              
#
#  Usage:  Login as root user to run this script.
# 
#          ./xtrabackup_mysql_database.sh              ( Run daily backup types according to configuration file settings )
#          ./xtrabackup_mysql_database.sh blog         ( Take a binary log backup, supporting 5.1 and later version only )
#          ./xtrabackup_mysql_database.sh force_full   ( Force a full backup, overwriting the daily backup type. )
#          ./xtrabackup_mysql_database.sh force_incr   ( Force a incremental backup, overwriting the daily backup type. )
#          ./xtrabackup_mysql_database.sh stream       ( Force a streamed compressed backup, overwriting the daily backup type. )
#          ./xtrabackup_mysql_database.sh remote       ( Force a remote backup, for Xtracbackup 2.0.3 version only )
#
# Standard cron jobs
# 0 0 * * * source /root/.bash_profile;/opt/dba_script/xtrabackup_mysql_database.sh > /opt/dba_script/xtrabackup_mysql_db.log 2>&1
# 30 * * * * source /root/.bash_profile;/opt/dba_script/xtrabackup_mysql_database.sh blog > /opt/dba_script/xtrabackup_mysql_binary.log 2>&1 
##############################################################################################################################
#  History : Jackey Lin       Enhance with auto switch to full backup mode                                         2013 08 22
#            Jackey Lin       Adjustable binary log back search time                                               2013 11 08
#            Jackey Lin       Abort and send alert if existing xtrabackup running                                  2013 12 10
#            Jackey Lin       Wrap abort in a function                                                             2013 12 11
#            Jackey Lin       Add lock-wait-timeout for Xtrabackup 2.1 to avoid "Waiting for table flush" problem  2014 02 10
##############################################################################################################################
#  Run environment parameter configuration file
##############################################################################################################################
. /opt/dba_script/xtrabackup_mysql_database.conf
##############################################################################################################################
export VERSION=20140210
SCRIPT_DIR=/opt/dba_script
TODAY_NO=`date "+%u"`
export HOSTNAME=`hostname`
export XTRABACKUPVER=`rpm -qa|grep xtrabackup`

if [ `echo $XTRABACKUPVER|grep 2.1|wc -l` -gt 0 ]
then
   export AbortOnWaitTimeOut=on
   echo "$XTRABACKUPVER is capable of handling lock wait timeout."
   echo "Lock wait timeout setting: $LOCK_WAIT_TIMEOUT seconds"
   echo "Lock wait threshld setting: $LOCK_WAIT_THRESHOLD seconds"
else
   export AbortOnWaitTimeOut=off
   echo "Lock wait feature will not be used."
fi

MAIL_SENDER="Xtrabackup@$HOSTNAME"
export MAIL_SENDER
MAILCONTENT=/opt/dba_script/xtrabackup_mysql_db.log
export MAILCONTENT

if [ -r /opt/dba_script/xtrabackup_mysql_db.log ]
then
   cat /opt/dba_script/xtrabackup_mysql_db.log > /opt/dba_script/xtrabackup_mysql_db.log.bak
   cat /dev/null > /opt/dba_script/xtrabackup_mysql_db.log
else
   touch /opt/dba_script/xtrabackup_mysql_db.log;
fi
#######################################################################################################################
#               Check Disk Free %
#######################################################################################################################
check_disk_usage () {
	
program_section="check_disk_usage"

echo "Checking storage usage of backup mount point: $BACKUP_MOUNTPOINT"
MOUNTPOINTMATCH="false"
echo $MOUNTPOINTMATCH > /tmp/xtrabackup_mountpoint_match.log

declare -i STORAGEUSE

df -h | grep / | awk '{print $6" "$5}' | cut -f1 -d % > /tmp/backup_check_disk.tmp
    
cat /tmp/backup_check_disk.tmp | while read LINE
do
    case $LINE in
	  
	  "") ;;
	  *)
	     
		 MOUNTPOINT=`echo $LINE | awk '{print $1}'`
		 export MOUNTPOINT
		    
	     STORAGEUSE=`echo $LINE | awk '{print $2}'`
		 export STORAGEUSE

		 if [ $MOUNTPOINT = $BACKUP_MOUNTPOINT ]
		 then
		
		     if [ $STORAGEUSE -gt $STORAGE_USAGE_PERC ]
		     then
		        echo "Error! Mount point $MOUNTPOINT usage $STORAGEUSE % has exceeded threshold $STORAGE_USAGE_PERC %. Backup will abort."
		        echo "Error! Mount point $MOUNTPOINT usage $STORAGEUSE % has exceeded threshold $STORAGE_USAGE_PERC %. Backup will abort." >> $MAILCONTENT
		        
		        mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
		        
		        send_mail $program_section
		        
		        echo "Program exiting.."
		        echo "true" > /tmp/xtrabackup_abort.log
	            sleep 2;
		        break;
		        
		     else
		        echo "OK! Mount point $MOUNTPOINT usage $STORAGEUSE %, is under threshold $STORAGE_USAGE_PERC %. Backup will proceed."
		        echo "false" > /tmp/xtrabackup_abort.log
		     fi
		    
		     MOUNTPOINTMATCH="true"
		     echo $MOUNTPOINTMATCH > /tmp/xtrabackup_mountpoint_match.log
		   
		fi 		    
	    ;;
     esac
done

if [ -r /tmp/xtrabackup_abort.log ]
then
   if [ `cat /tmp/xtrabackup_abort.log` = "true" ]
   then
      echo "Bye!"
      exit 1;
   fi
fi 

if [ -r /tmp/xtrabackup_mountpoint_match.log ]
then

   if [ `cat /tmp/xtrabackup_mountpoint_match.log` = "false" ]
   then
      echo "Warning: backup mountpoint $BACKUP_MOUNTPOINT does not exist."
      echo "Storage usage check will not function correctly, but backup is still allowed to proceed."
   fi
fi

}

##############################################################################################################################
#        Check if previous extrabackup is still running, if fond, abort.   ###################################################
##############################################################################################################################
abort_on_running (){

program_section="abort_on_running"
	
export CURRBACKUPPRC=`ps -ef|grep xtrabackup|wc -l`

if [ "$CURRBACKUPPRC" -gt 5 ]
then
 
    echo "There are $CURRBACKUPPRC backup process already running, backup will not proceed." >> $MAILCONTENT
    echo "" >> $MAILCONTENT
    ps -ef|grep xtrabackup >> $MAILCONTENT
            
    mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
    send_mail $program_section
	echo "Program exiting.."
	sleep 2;
	exit 1;
	
else    	
    echo "No previous backup process is found running, backup will proceed."
fi
}
##############################################################################################################################
#        Read previous backup directory and type #############################################################################
##############################################################################################################################
if [ ! -r "$SCRIPT_DIR"/last_backup.ctrl ]
then
  echo "export BACKUPDIR_PREV=unknown" > $SCRIPT_DIR/last_backup.ctrl
  echo "export BACKUPTYPE_PREV=unknown" >> $SCRIPT_DIR/last_backup.ctrl
else
  . $SCRIPT_DIR/last_backup.ctrl
fi
##############################################################################################################################
#        Mailer
##############################################################################################################################
send_mail () {
		
    if [ "$DEBUG" = "Y" ]
    then 
       echo "Sending email (send_mail)"
    fi      
    
    MAIL_COMMAND="mail"
    type mail >/dev/null 2>&1 || { echo >&2 "mail rpm not installed."; MAIL_COMMAND=""; export MAIL_COMMAND; }
    
    if [ "$MAIL_COMMAND" = "" ]
    then
       MAIL_COMMAND="sendmail"
       type sendmail >/dev/null 2>&1 || { echo >&2 "sendmail rpm not installed."; MAIL_COMMAND=""; export MAIL_COMMAND; }
    fi
    
    export MAIL_COMMAND
    echo "Mail utility found: $MAIL_COMMAND"
			
	echo "Sending email alert for backup error."
	MAILTITLE="Alert: MySQL backup failed on $HOSTNAME $1"
	echo $MAILTITLE
	
	if [ "$MAIL_COMMAND" = "mail" ] 
	then		    
	    mail -s "$MAILTITLE" $dba_mail < $MAILCONTENT
	    
	elif [ "$MAIL_COMMAND" = "sendmail" ] 
	then
	    sed -i "1i Subject: $MAILTITLE" $MAILCONTENT
	    sendmail -F $MAIL_SENDER -t $dba_mail < $MAILCONTENT
    else
	    echo "Mail utility not installed, program aborting.."
	    sleep 2
	    echo "Bye!"
	    exit 1;
    fi
    	   	
	echo ""
}
##############################################################################################################################
#       Create backup directories if they dont' exist
##############################################################################################################################
create_backup_dir () {
  
  typeset -i WeekDay
  WeekDay=1
  
  program_section="Create 7 backup directories for 7 week days."
  echo $program_section
    
  while [ ! "$WeekDay" -gt 7  ]
  do
    
     if [ ! -d "$BACKUP_BASE"/daily/"$WeekDay" ] 
     then
          program_section="Creating backup directory $BACKUP_BASE/daily/$WeekDay"
          echo $program_section
          
          mkdir -p $BACKUP_BASE/daily/$WeekDay     
          chown -Rf mysql:mysql $BACKUP_BASE/daily/$WeekDay 
     fi
   
     let WeekDay=$WeekDay+1;
   
  done;
  
  if [ ! -d "$BACKUP_BASE/full" ] 
  then
      program_section="Creating full backup directory $BACKUP_BASE/full"
      echo $program_section
      mkdir -p $BACKUP_BASE"/full"
      chown -Rf mysql:mysql $BACKUP_BASE"/full"
  fi
  
  if [ ! -d "$BACKUP_BASE/incr" ] 
  then
      program_section="Creating incremental directory $BACKUP_BASE/incr"
      echo $program_section
      mkdir -p $BACKUP_BASE"/incr"
      chown -Rf mysql:mysql $BACKUP_BASE"/incr"
  fi
  
  if [ ! -d "$BACKUP_BASE/blog" ] 
  then
      program_section="Creating full backup directory $BACKUP_BASE/blog"
      echo $program_section
      mkdir -p $BACKUP_BASE"/blog"
      chown -Rf mysql:mysql $BACKUP_BASE"/blog"
  fi
  
  if [ ! -d "$BACKUP_BASE/stream" ] 
  then
      program_section="Creating stream backup directory $BACKUP_BASE/stream"
      echo $program_section
      mkdir -p $BACKUP_BASE"/"stream 
      chown -Rf mysql:mysql $BACKUP_BASE"/stream"
  fi
  
  if [ ! -d "$BACKUP_BASE/daily/control" ] 
  then
      program_section="Creating control directory $BACKUP_BASE/daily/control"
      echo $program_section
      mkdir -p $BACKUP_BASE"/daily/control"
      chown -Rf mysql:mysql $BACKUP_BASE"/daily/control"
  fi
  
  chmod -Rf 775 $BACKUP_BASE
}

##############################################################################################################################
#     Backup full database
##############################################################################################################################
backup_db_full () {
   
   if [ "$1" = "force" ]
   then
      program_section="Forced full backup specified, removing full backup files"
      echo $program_section
      rm -Rf $BACKUP_BASE/full
      chown -Rf mysql:mysql $BACKUP_BASE
      BDIR=$BACKUP_BASE/full
      chmod -Rf 775 $BACKUP_BASE
   else
      program_section="Full backup called by daily backup."
      echo $program_section
      YYYYMMDDHHMI=`date +%Y%m%d%H%M`
      export YYYYMMDDHHMI
      BDIR=$BACKUP_BASE/daily/$TODAY_NO"/"$YYYYMMDDHHMI      
   fi 
   
   echo $BDIR > $SCRIPT_DIR/backup_dir.log
    
   echo "The backup compression setting is :" $BACKUP_COMPRESS
   
   if [ "$BACKUP_COMPRESS" != "on" ]
   then   
       
       if [ $AbortOnWaitTimeOut = "on" ]
       then
           program_section="Starting full database backup (no compress) to $BDIR with lock-wait-timeout."
           echo $program_section       
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --lock-wait-timeout=$LOCK_WAIT_TIMEOUT --lock-wait-threshold=$LOCK_WAIT_THRESHOLD --lock-wait-query-type=all --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup $BDIR
       else
           program_section="Starting full database backup (no compress) to $BDIR"
           echo $program_section       
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup $BDIR
           #/usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --no-lock $BDIR
       fi
       
   elif [ "$BACKUP_COMPRESS" = "on" ]
   then
                
       if [ $AbortOnWaitTimeOut = "on" ]
       then
            program_section="Starting full database backup (compressed) to $BDIR with lock-wait-timeout."
            echo $program_section
            /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --compress --throttle=$BACKUP_THROTTLE --lock-wait-timeout=$LOCK_WAIT_TIMEOUT --lock-wait-threshold=$LOCK_WAIT_THRESHOLD --lock-wait-query-type=all --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup $BDIR
       else
            program_section="Starting full database (compressed) backup to $BDIR"
            echo $program_section
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --compress --throttle=$BACKUP_THROTTLE --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup $BDIR
       fi 
              
   else
       program_section="Invalid value for BACKUP_COMPRESS :" $BACKUP_COMPRESS
       echo $program_section       
   fi
   
   echo "Copying MySQL configuration file /etc/my.cnf"
   cp /etc/my.cnf $BDIR/my.cnf
   
   if [ "$?" == "1" ]
   then
	   echo "Full backup encountered problem, program exit with error." >> /opt/dba_script/xtrabackup_mysql_db.log
	   
	   mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
      
	   send_mail $program_section
	   
       exit 1
       
   elif [ "$1" != "force" ]
   then
       if [ -r "$BDIR/xtrabackup_checkpoints" ]
       then
       
          program_section="Recording last backup to control file"
          echo $program_section
          echo "export BACKUPDIR_PREV=$BDIR" > $SCRIPT_DIR/last_backup.ctrl
          echo "export BACKUPTYPE_PREV=full" >> $SCRIPT_DIR/last_backup.ctrl
          
          program_section="Recording last full backup to full backup control file"
          echo $program_section
          echo $BDIR > $SCRIPT_DIR/last_backup_full.ctrl
        
          echo "" >> $BACKUP_BASE"/daily/control/backup_history.log"
          echo "Full backup completed : $BDIR" >> $BACKUP_BASE"/daily/control/backup_history.log"
          echo "Content of $BDIR/xtrabackup_checkpoints" >> $BACKUP_BASE"/daily/control/backup_history.log"
          cat $BDIR"/xtrabackup_checkpoints" >> $BACKUP_BASE"/daily/control/backup_history.log"
          
          RESTORESCRIPT1=$BACKUP_BASE"/daily/control/restore_db_1_prepare.sh"
          export RESTORESCRIPT1
          RESTORESCRIPT2=$BACKUP_BASE"/daily/control/restore_db_2_copyback.sh"
          export RESTORESCRIPT2
          
          program_section="Reset $RESTORESCRIPT1 with prepare command to full backup base."
          echo $program_section
          
          cat /dev/null > $RESTORESCRIPT1
          
          if [ "$BACKUP_COMPRESS" = "on" ]
          then
             echo "cd $BDIR" >> $RESTORESCRIPT1
             echo "for bf in \`find . -iname \"*\\.qp\"\`; do qpress -d \$bf \$(dirname \$bf) && rm -f \$bf; done" >> $RESTORESCRIPT1
          fi
          
          echo "/usr/bin/innobackupex-1.5.1 --apply-log --redo-only $BDIR" >> $RESTORESCRIPT1
          
          echo "/usr/bin/innobackupex-1.5.1 --apply-log $BDIR" > $RESTORESCRIPT2
          echo "/usr/bin/innobackupex-1.5.1 --copy-back $BDIR" >> $RESTORESCRIPT2
          
       else
          program_section="Checkpoint file $BDIR/xtrabackup_checkpoints not available, full backup may not be successful."
          echo $program_section
                     
          mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
      
	      send_mail $program_section

       fi 
   fi
   
   check_log;
}
##############################################################################################################################
# Backup incremental database
##############################################################################################################################
backup_db_incr () {    
   
   if [ -r $SCRIPT_DIR/last_backup_full.ctrl ] 
   then
      echo "Reading last backup control file $SCRIPT_DIR/last_backup_full.ctrl"
      export FULL_BACKUPDIR_PREV=`cat $SCRIPT_DIR/last_backup_full.ctrl`
   else
      export FULL_BACKUPDIR_PREV=""
   fi
   
   if [ ! -d $FULL_BACKUPDIR_PREV ]
   then
      echo "************************************************************************************************************"
      echo "Full backup directory "$FULL_BACKUPDIR_PREV" was not found. Forcing to become a full backup.                "
      echo "************************************************************************************************************"
      main_backup_full;
      exit 0
   elif [ "$FULL_BACKUPDIR_PREV" = "" ]
   then
      echo "************************************************************************************************************"
      echo "Full backup was not found. This incremental backup is forced to a full backup.                              "
      echo "************************************************************************************************************"
      main_backup_full;
      exit 0
   else
      echo "Full backup found in $FULL_BACKUPDIR_PREV, incremental backup continue."
      
   fi
   
   YYYYMMDDHHMI=`date +%Y%m%d%H%M`
   BDIR=$BACKUP_BASE/daily/$TODAY_NO"/"$YYYYMMDDHHMI
   echo $BDIR > $SCRIPT_DIR/backup_dir.log
        
   if [ "$BACKUP_COMPRESS" != "on" ]
   then         
   
       if [ $AbortOnWaitTimeOut = "on" ]
       then
           program_section="Starting incremetnal database backup (no compress) to $BDIR with lock-wait-timeout."
           echo $program_section
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --lock-wait-timeout=$LOCK_WAIT_TIMEOUT --lock-wait-threshold=$LOCK_WAIT_THRESHOLD --lock-wait-query-type=all --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --incremental $BDIR --incremental-basedir=$BACKUPDIR_PREV
       else
           program_section="Starting incremetnal database backup (no compress) to $BDIR"
           echo $program_section
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --incremental $BDIR --incremental-basedir=$BACKUPDIR_PREV
       fi
       
   elif [ "$BACKUP_COMPRESS" = "on" ]
   then       
       if [ $AbortOnWaitTimeOut = "on" ]
       then
           program_section="Starting incremetnal database backup (compressed) to $BDIR with lock-wait-timeout."
           echo $program_section
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --compress --throttle=$BACKUP_THROTTLE --lock-wait-timeout=$LOCK_WAIT_TIMEOUT --lock-wait-threshold=$LOCK_WAIT_THRESHOLD --lock-wait-query-type=all --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --incremental $BDIR --incremental-basedir=$BACKUPDIR_PREV
       else
           program_section="Starting incremetnal database backup (compressed) to $BDIR"
           echo $program_section
           /usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --compress --throttle=$BACKUP_THROTTLE --no-timestamp --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --incremental $BDIR --incremental-basedir=$BACKUPDIR_PREV
       fi
   else
       program_section="Invalid value for BACKUP_COMPRESS :" $BACKUP_COMPRESS
       echo $program_section       
   fi
   
   echo "Copying MySQL configuration file /etc/my.cnf"
   cp /etc/my.cnf $BDIR/my.cnf      
   
   if [ "$?" == "1" ]
   then
	   echo "Incremental backup encountered problem, program exit with error." >> /opt/dba_script/xtrabackup_mysql_db.log
	   
	   mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
      
	   send_mail $program_section
	   
       exit 1
   else
       if [ -r "$BDIR/xtrabackup_checkpoints" ]
       then
          echo "Recording last backup to control file"
          echo "export BACKUPDIR_PREV=$BDIR" > $SCRIPT_DIR/last_backup.ctrl
          echo "export BACKUPTYPE_PREV=incr" >> $SCRIPT_DIR/last_backup.ctrl
        
          echo "" >> $BACKUP_BASE"/daily/control/backup_history.log"
          echo "Incremental backup completed : $BDIR" >> $BACKUP_BASE"/daily/control/backup_history.log"
          echo "Content of $BDIR/xtrabackup_checkpoints" >> $BACKUP_BASE"/daily/control/backup_history.log"
          cat $BDIR"/xtrabackup_checkpoints" >> $BACKUP_BASE"/daily/control/backup_history.log"
          
          RESTORESCRIPT1=$BACKUP_BASE"/daily/control/restore_db_1_prepare.sh"
          export RESTORESCRIPT1
        
          if [ "$BACKUP_COMPRESS" = "on" ]
          then
             echo "cd $BDIR" >> $RESTORESCRIPT1
             echo "for bf in \`find . -iname \"*\\.qp\"\`; do qpress -d \$bf \$(dirname \$bf) && rm -f \$bf; done" >> $RESTORESCRIPT1
          fi
          
          echo "Append $BACKUP_BASE/control/restore_db.sh with prepare command to incremental backup."
          echo "/usr/bin/innobackupex-1.5.1 --apply-log --redo-only $FULL_BACKUPDIR_PREV --incremental-dir=$BDIR" >> $RESTORESCRIPT1
       
       else
          program_section="Checkpoint file $BDIR/xtrabackup_checkpoints not available, incremental backup may not be successful."
          echo $program_section
          
          mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$program_section' )";
      
	      send_mail $program_section

       fi  
   fi
   
   check_log;
}
##############################################################################################################################
# Backup binary log
##############################################################################################################################
backup_binary_log () {
	
MyVarDataDir=$(echo "SELECT @@datadir" | mysql --skip-column-names -udbabackup -p'ob$cur3')
export MyVarDataDir
echo "Data directory is "$MyVarDataDir

MyVarLogBin=$(echo "SELECT @@log_bin" | mysql --skip-column-names -udbabackup -p'ob$cur3')
export MyVarLogBin
echo "Binary log feature is "$MyVarLogBin

if [ "$MyVarLogBin" = "ON" ]
then
  MyLogBinFormat="*bin*"
  export MyLogBinFormat

elif [ "$MyVarLogBin" = "OFF" ]
then
  echo "Binary log is not turned on, backup binary log is not needed."
  echo "Backup binary log program exiting."
  sleep 2
  exit 0;
else
  echo "Binary log is turned on using a non-default format"
  MyLogBinFormat=$MyVarLogBin
  export MyLogBinFormat
fi

#echo "Copying binary log of past 1 day to "$BACKUP_BASE"/blog/"
#/usr/bin/find $MyVarDataDir$MyLogBinFormat -maxdepth 1 -ctime -1 | xargs -i cp -u {} $BACKUP_BASE"/blog/";
echo "Copying binary log of past $BINLOG_SEARCH_HOUR minutes to "$BACKUP_BASE"/blog/ if it does not exist"
/usr/bin/find $MyVarDataDir$MyLogBinFormat -maxdepth 1 -mmin -$BINLOG_SEARCH_HOUR | xargs -i cp -u {} $BACKUP_BASE"/blog/";

}

##############################################################################################################################
# Stream full backup to a compressed file  ( this causes severe I/O but save storage )
##############################################################################################################################
backup_db_full_stream () {	
   
program_section="Finding data dir from parameter file"
echo $program_section
datadir=`cat /etc/my.cnf | grep datadir | sed 's/ //g' | cut -d '=' -f2`

program_section="Setting file name extention YYYYMMDD-HH24"
echo $program_section
fname=`date +%Y%m%d-%H`

STREAMCOMPRESSFILE=$BACKUP_BASE"/stream/${fname}".tar.gz
export STREAMCOMPRESSFILE

program_section="Bakup MySQL full database and stream to zipped file" $STREAMCOMPRESSFILE
echo $program_section

echo "Start of backup time" `date`
/usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --stream=tar ./ | gzip - > $STREAMCOMPRESSFILE


if [ "$?" == "1" ]
then
    echo "Stream backup encountered problem, program exit with error." >> /opt/dba_script/xtrabackup_mysql_db.log
	   
	mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, remarks ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), 'stream compressed','$STREAMCOMPRESSFILE', 'Failed', '$program_section' )";
      
	send_mail $program_section
	   
    exit 1
else
    BACKUP_SIZE=`du -sh $BACKUP_BASE"/stream/${fname}".tar.gz |awk '{print $1}'`
    export BACKUP_SIZE
   
    mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, size ) VALUES ( '$YYYYMMDDHHMI', NOW(), NOW(), 'stream compressed','$STREAMCOMPRESSFILE', 'OK', '$BACKUP_SIZE' )";
  
fi

echo "End of backup time" `date`
}

##############################################################################################################################
# Backup full database to a remote server ( You need to configure public / private key )
##############################################################################################################################
backup_db_full_remote () {
	
echo "Backuping full database to remote host" $REMOTE_HOST "directory" $REMOTE_BACKUPDIR
echo "Getting data dir as temp dir"
#DataDir=`cat /etc/my.cnf | grep datadir | sed 's/ //g' | cut -d '=' -f2`
#RemoteTmpDir=$DataDir"/xtrabackup_remote_tmp"
#mkdir -p $RemoteTmpDir

echo "Start of remote backup time" `date`
/usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --remote-host=$REMOTE_USER@$REMOTE_HOST $REMOTE_BACKUPDIR --tmpdir=$REMOTE_TMPDIR --scpopt="-Cp -c arcfour"
#/usr/bin/innobackupex-1.5.1 --user=dbabackup --password='ob$cur3' --throttle=$BACKUP_THROTTLE --defaults-file=/etc/my.cnf --ibbackup=xtrabackup --remote-host=$REMOTE_USER@$REMOTE_HOST $REMOTE_BACKUPDIR --scpopt="-Cp -c arcfour"

echo "End of remote backup time" `date`
}
##############################################################################################################################
# Perform cleanup: remove backup directories older than retention policy
##############################################################################################################################
purge_backup () {

declare -i RETDAYS
let RETDAYS=$RETENTION_DAYS-1
	
echo "Removing old backup directory from" $BACKUP_BASE"/daily for past" $RETENTION_DAYS "days."
if [ -d "$BACKUP_BASE/daily" ]
then
   /usr/bin/find $BACKUP_BASE"/daily/1" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/2" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/3" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/4" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/5" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/6" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
   /usr/bin/find $BACKUP_BASE"/daily/7" -maxdepth 1 -type d -mtime +$RETDAYS -exec echo "Removing sub directory => {}" \; -exec rm -Rf "{}" \;
fi

if [ -d "$BACKUP_BASE/full" ]
then
   echo "Removing old backup files from" $BACKUP_BASE"/full for past" $RETENTION_DAYS "days."
   /usr/bin/find $BACKUP_BASE"/full/" -mtime +$RETDAYS -exec echo "Removing full backup files => {}" \; -exec rm -Rf "{}" \;
fi

if [ -d "$BACKUP_BASE/incr" ]
then
echo "Removing old backup files from" $BACKUP_BASE"/incr for past" $RETENTION_DAYS "days."
/usr/bin/find $BACKUP_BASE"/incr/" -mtime +$RETDAYS -exec echo "Removing incremental backup files => {}" \; -exec rm -Rf "{}" \;
fi

if [ -d "$BACKUP_BASE/blog" ]
then
echo "Removing old backup files from" $BACKUP_BASE"/blog for past" $RETENTION_DAYS "days."
/usr/bin/find $BACKUP_BASE"/blog/" -mtime +$RETDAYS -exec echo "Removing binary log backup files => {}" \; -exec rm -Rf "{}" \;
fi

if [ -d "$BACKUP_BASE/blog" ]
then
   echo "Removing all relay logs from" $BACKUP_BASE"/blog"
   /usr/bin/find $BACKUP_BASE"/blog/" -name *-relay-bin* -exec rm {} \;
fi

if [ -d "$BACKUP_BASE/stream" ]
then
   echo "Removing old backup files from" $BACKUP_BASE"/stream for past" $RETENTION_DAYS "days."
   /usr/bin/find $BACKUP_BASE"/stream/" -mtime +$RETDAYS -exec echo "Removing streams backup files => {}" \; -exec rm -Rf "{}" \;
fi

echo "Purging backup log table record of 30 days ago"
mysql -N -r -B -udbabackup -p'ob$cur3' -e"DELETE FROM mysql.dba_backup_log WHERE start_time < DATE_SUB(CURDATE(), INTERVAL 30 DAY)";
      
}
##############################################################################################################################
# Move the backup files to another dump folder
##############################################################################################################################
move_backup () {
	
	if [ "$COPY_PATH" != "" ]
	then
	    echo "Copy path is configured. Copy action will be executed"
	    
	    if [ -d "$COPY_PATH" ]
	    then
	        echo "Copy path verified to be existing."
	       
	        SOURCEDIR=`cat $SCRIPT_DIR/backup_dir.log`
	   
	        if [ -d "$SOURCEDIR" ]
	        then
	            NEWSUBDIR=`date +%Y%m%d%H%M`
	            echo "Making new sub directory on target path."
	            mkdir -p $COPY_PATH/$NEWSUBDIR
	            
	            echo "Backup directory "$SOURCEDIR "verified to be existing."
	            echo "Copying backup file from "$SOURCEDIR" to "$COPY_PATH"."
	            cp -Rf $SOURCEDIR $COPY_PATH/$NEWSUBDIR
	   
	            if [ "$?" != "0" ]; then
	               echo "Warning: Copying backup file from "$SOURCEDIR" to "$COPY_PATH" failed.">> /opt/dba_script/xtrabackup_mysql_db.summary 
	            fi
	            
	            echo "Removing files from "$SOURCEDIR
	            rm -Rf $SOURCEDIR
	            
	            if [ "$?" != "0" ]; then
	               echo "Removing files from "$SOURCEDIR "failed." >> /opt/dba_script/xtrabackup_mysql_db.summary 
	            fi
	            
	            echo "Purging old backup directory from" $COPY_PATH" for past" $COPY_RETENTION_DAYS "days."
                /usr/bin/find $COPY_PATH -type d -ctime +$COPY_RETENTION_DAYS -exec rm -Rf {} \;
                
                if [ "$?" != "0" ]; then
	               echo "Purging old backup directory from" $COPY_PATH" for past" $COPY_RETENTION_DAYS "days failed.">> /opt/dba_script/xtrabackup_mysql_db.summary 
	            fi

	        else
	            echo "Backup directory "$SOURCEDIR "verified to be non-existing, no action will be carried out."
	        fi
	    fi 
	else
	    echo "Copy path is not configured. No copy action will be executed."
	fi
}
##############################################################################################################################
# Check backup detail log and generate summary log
##############################################################################################################################
check_log () {
	
   LOGCHECKTIME=`date "+%Y-%m-%d %H:%M:%S"`
   BACKUP_SIZE=`du -sh $BDIR|awk '{print $1}'`
   export BACKUP_SIZE
   
   if [ `cat /opt/dba_script/xtrabackup_mysql_db.log | grep "completed OK" | wc -l` -gt 0 ]
   then
      program_section="xtrabackup_mysql_db.log indicated the backup was successful."
      echo $program_section
      echo "Checked backup trace from xtrabackup_mysql_db.log"  > /opt/dba_script/xtrabackup_mysql_db.summary
      echo "Backup log xtrabackup_mysql_db.log check time :$LOGCHECKTIME" >> /opt/dba_script/xtrabackup_mysql_db.summary
      echo "completed OK" >> /opt/dba_script/xtrabackup_mysql_db.summary
      
      mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, size ) VALUES ( '$YYYYMMDDHHMI', '$BACKUPSTARTTIME', NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'OK', '$BACKUP_SIZE')";      
      
   elif [ `cat /opt/dba_script/xtrabackup_mysql_db.log|wc -l` -gt 0 ]  # If /opt/dba_script/xtrabackup_mysql_db.log is not empty
   then
   
      program_section="xtrabackup_mysql_db.log is not empty and OK keyword not found."
      echo $program_section
      echo "Checked backup trace from xtrabackup_mysql_db.log" > /opt/dba_script/xtrabackup_mysql_db.summary
      echo "Backup log xtrabackup_mysql_db.log check time :$LOGCHECKTIME" >> /opt/dba_script/xtrabackup_mysql_db.summary
      echo "Backup failed." >> /opt/dba_script/xtrabackup_mysql_db.summary
      send_mail $program_section
      
      mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, size, remarks ) VALUES ( '$YYYYMMDDHHMI', '$BACKUPSTARTTIME', NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Failed', '$BACKUP_SIZE', '$program_section' )";
   
   else  # If /opt/dba_script/xtrabackup_mysql_db.log is empty
   
      program_section="xtrabackup_mysql_db.log is empty, the backup script could be started manually."
      echo $program_section
      echo "Checked backup trace from xtrabackup_mysql_db.log"  > /opt/dba_script/xtrabackup_mysql_db.summary
      echo "Backup log xtrabackup_mysql_db.log check time :$LOGCHECKTIME" >> /opt/dba_script/xtrabackup_mysql_db.summary
      echo "Backup status unknown." >> /opt/dba_script/xtrabackup_mysql_db.summary
        
      mysql -N -r -B -udbabackup -p'ob$cur3' -e"INSERT INTO mysql.dba_backup_log ( id, start_time, end_time, backup_type, backup_file, status, size, remarks ) VALUES ( '$YYYYMMDDHHMI', '$BACKUPSTARTTIME', NOW(), '$BACKUPTYPE_TODAY','$BDIR', 'Unkown', '$BACKUP_SIZE', 'Log is emtpy. But the backup could be successful if you have seen completed OK on the screen.' )";
     
   fi
}
##############################################################################################################################
#               MySQL service status
##############################################################################################################################
db_service_status () {

if [ -r /etc/init.d/mysql ]
then
   if [ `service mysql status | grep "MySQL running" | wc -l` = "1" ] 
   then      
       echo "MySQL service is running on this node, backup will proceed."
   elif [ `ps -ef|grep "mysqld_safe" | wc -l` -gt 1 -a `cat /etc/issue |grep "Ubuntu"| wc -l` -eq 1 ]
   then
       echo "MySQL service is running on this Unbuntu server."           
   else 
       echo "MySQL service is NOT running on this node, backup will abort."
       sleep 3
       exit 1;
   fi
fi

if [ -r /etc/init.d/mysqld ]
then
   
   if [ `service mysqld status|grep "is running"|wc -l` = "1" ] 
   then     
       echo "MySQL service is running on this node."     
   else
       echo "MySQL service is NOT running on this node."
       sleep 3
       exit 1;
   fi

fi
  
}
##############################################################################################################################
# Main program for Streaming full backup
##############################################################################################################################
main_backup_stream () {
  
  abort_on_running;
  check_disk_usage;
  db_service_status;
  
  echo "Starting to backup database by streaming."
  date
  echo "Calling function to create backup directory."
  create_backup_dir;
  
  echo "Calling function to backup full db by streaming and compression."
  backup_db_full_stream;
  
  echo "Calling function to purge old backup files."
  purge_backup; 
}
##############################################################################################################################
# Main program for remote full backup
##############################################################################################################################
main_backup_remote () {

  abort_on_running;
  db_service_status;
  
  echo "Calling function to backup full db to remote host."
  backup_db_full_remote;
 
}
##############################################################################################################################
# Main program for full backup
##############################################################################################################################
main_backup_full () {

  abort_on_running;
  check_disk_usage;
  db_service_status;
  
  echo "Calling function to purge old backup files: first round."
  purge_backup;
  
  echo "Starting to backup database fully."
  date
  echo "Calling function to create backup dir."
  create_backup_dir;
  
  if [ "$1" = "force" ]
  then 
    echo "Calling function to backup database forced fully."
    backup_db_full "force";
  else
    echo "Calling function to backup database daily fully."
    backup_db_full;
  fi

  echo "Calling function to purge old backup files: second round."
  purge_backup;
  
  if [ "$COPY_PATH" != "" ]
  then  
     echo "Calling function to move backup files."
     move_backup;
  fi
}
##############################################################################################################################
# Main program for incremental backup
##############################################################################################################################
main_backup_incr () {

  abort_on_running;
  check_disk_usage;
  db_service_status;
  
  echo "Starting to backup database incremental."
  date
  echo "Calling function to create backup directory."
  create_backup_dir;
  
  echo "Calling function to backup database with different incremental level."
  backup_db_incr;

  echo "Calling function to purge old backup files."
  purge_backup;
  
  if [ "$COPY_PATH" != "" ]
  then
      echo "Calling function to move backup files."
      move_backup;
  fi
  
}
##############################################################################################################################
# Main program for binary log backup
##############################################################################################################################
main_backup_binlog () {
  
  check_disk_usage;
  db_service_status;
  
  echo "Calling function to purge old backup files: first round"
  purge_backup;
  
  echo "Starting to backup binary log"
  date
  echo "Calling function to create backup dir"
  create_backup_dir;
  
  echo "Calling function to backup binary log"
  backup_binary_log;

  echo "Calling function to purge old backup files: second round"
  purge_backup;
  
}
##############################################################################################################################
# Find today's backup type
##############################################################################################################################
call_backup_type_today () {

  TODAY_NO=`date "+%u"`
  
  if [ "$TODAY_NO" -eq 1 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY1    
  elif [ "$TODAY_NO" -eq 2 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY2  
  elif [ "$TODAY_NO" -eq 3 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY3
  elif [ "$TODAY_NO" -eq 4 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY4
  elif [ "$TODAY_NO" -eq 5 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY5
  elif [ "$TODAY_NO" -eq 6 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY6
  elif [ "$TODAY_NO" -eq 7 ]
  then
      BACKUPTYPE_TODAY=$BACKUPTYPE_DAY7
  fi
     
  export TODAY_NO;
  export BACKUPTYPE_TODAY;
  
  if [ "$BACKUPTYPE_TODAY" = "full" ]
  then
     echo "Today's backup type is full."
     main_backup_full;
     
  elif [ "$BACKUPTYPE_TODAY" = "incr" ]
  then
     echo "Today's backup type is incremental."
     main_backup_incr;
  
  else
     echo "Unrecognizable backup type, program exit with error"
     exit 1;     
  fi
}

##############################################################################################################################
#               Main Switch
##############################################################################################################################
export SWITCH=$1

BACKUPSTARTTIME=`date "+%Y-%m-%d %H:%M:%S"`
export BACKUPSTARTTIME

case $1 in
	  
	  "")
	  call_backup_type_today;
	  ;;
	  
	  "force_full") 
	  main_backup_full "force";
	  ;;
	  
	  "force_incr") 
	  main_backup_incr;
	  ;;
	  
	  "blog") 
	  main_backup_binlog;
	  ;;
	  
	  "stream") 
	  main_backup_stream;
	  ;;  
	  
	  "remote") 
	  main_backup_remote;
	  ;;
	  
	  *)
	  call_backup_type_today;
	  ;;
esac