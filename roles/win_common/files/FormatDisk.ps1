#Format Disk to 64kb and change the drive letter to D and set name to DATA
$Disk = Get-Disk -Number 1

Set-Disk -InputObject $Disk -IsOffline $false

Initialize-Disk -InputObject $Disk

New-Partition $Disk.Number -UseMaximumSize -DriveLetter D

Format-Volume -DriveLetter D -FileSystem NTFS -AllocationUnitSize 65536 -NewFileSystemLabel DATA -Confirm:$false