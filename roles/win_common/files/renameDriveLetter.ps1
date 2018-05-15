#Sample
#PS D:\PowerShell> .\renameDriveLetter.ps1 -NewDrvLetter Z:

[CmdletBinding()]
Param(
[Parameter(Mandatory=$True,
Position=1)]
[string]
[ValidatePattern("^[A-Z]{1}:{1}`$")]$NewDrvLetter
)
# Get Available CD/DVD Drive - Drive Type 5
$DvdDrv = Get-WmiObject -Class Win32_Volume -Filter "DriveType=5"
 
# Check if CD/DVD Drive is Available
if ($DvdDrv -ne $null)
{
 
# Get Current Drive Letter for CD/DVD Drive
$DvdDrvLetter = $DvdDrv | Select-Object -ExpandProperty DriveLetter
Write-Output "Current CD/DVD Drive Letter is $DvdDrvLetter"
 
# Confirm New Drive Letter is NOT used
if (-not (Test-Path -Path $NewDrvLetter))
{
 
# Change CD/DVD Drive Letter
$DvdDrv | Set-WmiInstance -Arguments @{DriveLetter="$NewDrvLetter"}
Write-Output "Updated CD/DVD Drive Letter as $NewDrvLetter"
}
else
{
Write-Output "Error: Drive Letter $NewDrvLetter Already In Use"
}
}
else
{
Write-Output "Error: No CD/DVD Drive Available !!"
}