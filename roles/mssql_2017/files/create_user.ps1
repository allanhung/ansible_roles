#Author      : Stella Pat
#Purpose     : Create SQL User
#DateCreated : 2018/4/23
#Example     : .\create_user.ps1 -Password <value>
#            : .\create_user.ps1 -Password Password123

Param([string]$Password)
$LoginName = "admin"

$Pass = ConvertTo-SecureString -String $Password -AsPlainText -Force
$Credential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $LoginName, $Pass

#Create sql login 
Add-SqlLogin -ServerInstance "localhost" -LoginName $LoginName -LoginType "SQLLogin" -LoginPSCredential $Credential -Enable -GrantConnectSql




