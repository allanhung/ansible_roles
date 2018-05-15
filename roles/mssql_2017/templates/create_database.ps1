#Author      : Stella Pat
#Purpose     : Create database
#DateCreated : 2018/4/20
#Example     : .\create_database.ps1 -databasename <value>
#            : .\create_database.ps1 -databasename NewDatabase

Param([string]$databasename)

#Create database
New-SQLDatabase -SqlInstance "localhost" -DatabaseName "$databasename" -Path "{{ install_disk }}:\MSSQL\Data"
