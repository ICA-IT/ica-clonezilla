# This code is part of the opsi.org project
# http://opsi.org
#
# Copyright (c) uib gmbh (www.uib.de)
# This sourcecode is owned by the uib gmbh, D55118 Mainz, Germany
# and published under the Terms of the GNU Affero General Public License.
# Text of the AGPL: http://www.gnu.org/licenses/agpl-3.0-standalone.html
# credits: http://www.opsi.org/credits/


#import ConfigParser
#from OPSI.Util.File import IniFile
#from OPSI.Backend.BackendManager import BackendManager
#from OPSI.Backend.JSONRPC import JSONRPCBackend
#from OPSI.Util import md5sum
#from hashlib import md5
#from twisted.conch.ssh import keys

#***************************************************************************
# Subversion:
# $Revision$
# $Author$
# $Date$
#***************************************************************************



################ local def #################################################################################
def initOpsiSetupLib():
	logger.notice(u"initOpsiSetupLib()")
	logger.notice(u"OpsiSetupLib $Revision$")
	logger.notice(u"OpsiSetupLib $Date$")
	#output = execute("sfdisk -l 2> /dev/null")
	#if not output:
	#	logger.notice(u"no disks with buildin sfdisk ...")
	#	logger.notice(u'looking for sfdisk in: '+DEPOT_MOUNT + '/bootimage_helper/sfdisk/%s/sfdisk' % getArchitecture())
	#	if os.path.exists(DEPOT_MOUNT + '/bootimage_helper/sfdisk/%s/sfdisk' % getArchitecture()):
	#		logger.notice(u"copy trusty sfdisk ....")
	#		depot.copy('/bootimage_helper/sfdisk/%s/sfdisk' % getArchitecture(), '/sbin/')
	#		execute("chmod 755 /sbin/sfdisk")

####################################### DISK / PARTITION FUNCTIONS  #############################################################
def getUuidFromDiskDevice(diskDevice = ""):
	# function to UUID from disk (not from partition)
	f = os.popen('blkid -s PTUUID -o value %s' % diskDevice)
	uuid = f.read()
	if uuid:
		uuid = uuid.strip()
		return uuid

def getUuidFromPartitionDevice(partDevice = ""):
	# function to UUID from partition (not from disk)
	f = os.popen('blkid -s UUID -o value %s' % partDevice)
	uuid = f.read()
	if uuid:
		uuid = uuid.strip()
		return uuid

def getPartuuidFromPartitionDevice(partDevice = ""):
	# function to UUID from partition (not from disk)
	f = os.popen('blkid -p -s PART_ENTRY_UUID -o value %s' % partDevice)
	uuid = f.read()
	if uuid:
		uuid = uuid.strip()
		return uuid
		
def getDiskuuidFromPartitionDevice(diskDevice = ""):
	# function to UUID from disk (not from partition)
	f = os.popen('blkid -s PART_ENTRY_UUID -o value %s' % diskDevice)
	uuid = f.read()
	if uuid:
		uuid = uuid.strip()
		uuid = uuid.split('-')[0]
		return uuid


def showDiskOrder(disks):
	logger.notice(u"Disk order:")
	for disk in disks:
		logger.notice(u" - {device} (rotational? {bool}) (sizeG {size}) (uuid {myuuid})".format(device=disk.device, bool=disk.rotational, size=int(float(disk.size)/(1024*1024*1024)), myuuid=getUuidFromDiskDevice(disk.device)))

def isRotationalDisk(diskDevice = ""):
	# function to check for ssd versus classic HD
	# http://linuxg.net/how-to-find-out-if-a-drive-is-a-ssd-or-an-hdd/
	logger.notice(u"Check if disk %s is ssd or classic (rotational) HD" % diskDevice)
	mydev = diskDevice.split('/')[2]
	f = os.popen('cat /sys/block/%s/queue/rotational' % mydev)
	rot = f.read()
	if rot:
		rot = rot.strip()
		if (rot == '1'):
			logger.notice(u"Disk %s is rotational (Classic HD)" % diskDevice)
			scriptMessageSubject.setMessage(u"Disk %s is rotational (Classic HD)" % diskDevice)
			return True
		else:
			logger.notice(u"Disk %s is not rotational (SSD)" % diskDevice)
			scriptMessageSubject.setMessage(u"Disk %s is not rotational (SSD)" % diskDevice)
			return False

def isBlockAlignedPartition(diskDevice = "", partitionNumber = "", useGpt = False):
	# function to check if a partition is created with correct block alignment
	# http://wiki.ubuntuusers.de/SSD/Alignment
	partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
	exitcode = os.system("parted -s %s align-check opt %d"  % (diskDevice, partitionNumber))
	if (0 == int(exitcode)):
		logger.notice(u"Partition %s has a correct block alignment" % (partitionDevicePath))
		scriptMessageSubject.setMessage(u"Partition %s has a correct block alignment" % (partitionDevicePath))
		return True
	else:
		logger.warning(u"Partition %s has no correct block alignment" % (partitionDevicePath))
		scriptMessageSubject.setMessage(u"Partition %s has no correct block alignment" % (partitionDevicePath))
		return False

def lvmClearVolumeGroups():
	logger.notice(u"Clear all existing LVM volume groups....")
	#exitcode = os.system("vgchange --activate y  2>> /dev/null")
	exitcode = os.system("vgchange --activate y 2> /dev/null")
	output = execute("vgs --noheadings 2> /dev/null")
	volgroups = []
	for line in output:
		volgroups.append(line.split()[0])
	for volg in volgroups:
		logger.notice(u"remove volume group: %s" % volg)
		#exitcode = os.system("vgremove --force %s 2>> /dev/null" % volg)
		output = execute("lvs --noheadings %s 2> /dev/null" % volg)
		vols = []
		for line in output:
			vols.append(line.split()[0])
			for vol in vols:
				try:
					execute("umount /dev/mapper/%s-%s 2> /dev/null" % (volg, vol))
				except:
					pass
		execute("vgremove --force %s 2> /dev/null" % volg)
	logger.notice(u"Remove all dead Links in /dev....")
	execute("find /dev -xtype l -delete -print")
	logger.notice(u"Remove all empty directories in /dev....")
	# do not break if not deletable
	exitcode = os.system("find /dev -empty -type d -delete -print 2> /dev/null")
	logger.notice(u"Look for still existing LVM volume groups....")
	output = execute("vgs --noheadings 2> /dev/null")


def getPartitionDevicePath(diskDevice = "", partitionNumber = ""):
	# determine if disk.device file is like /dev/cciss/c0d0
	# if this device filename is detected, the partition numbers
	# has to extend with a p: /dev/cciss/c0d0p1
	partitionDevicePath = ''
	unixDevicePath = re.compile("c\dd\d").search(diskDevice)
	#logger.notice(u"unixDevicePath = %s" % bool(unixDevicePath))
	raidDevicePath = re.compile("md\d").search(diskDevice)
	#logger.notice(u"raidDevicePath = %s" % bool(unixDevicePath))
	nvmeDevicePath = re.compile("nvme\dn\d").search(diskDevice)
	mmcDevicePath = re.compile("mmcblk\d").search(diskDevice)

	if unixDevicePath:
		# extending PartitionNumber with a starting p
		partitionDevicePath = "%sp%s" % (diskDevice, partitionNumber)
	elif raidDevicePath:
		# extending PartitionNumber with a starting p
		partitionDevicePath = "%sp%s" % (diskDevice, partitionNumber)
	elif nvmeDevicePath:
		# extending PartitionNumber with a starting p
		partitionDevicePath = "%sp%s" % (diskDevice, partitionNumber)
	elif mmcDevicePath:
		# extending PartitionNumber with a starting p
		partitionDevicePath = "%sp%s" % (diskDevice, partitionNumber)
	else:
		partitionDevicePath = "%s%s" % (diskDevice, partitionNumber)
	#logger.notice(u"partitionDevicePath = %s" % partitionDevicePath)
	return partitionDevicePath

def testPartitionEx(diskDevice = "", partitionNumber = "", useGpt = False):
	partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
	# copied from posix.px line2045
	retries = 1
	while retries <= 6:
		#if os.path.exists(disk.getPartition(winpePartitionNumber)['device']):
		# disk do not work with gpt right now
		exitcode = os.system("test -b %s >> /dev/null 2>&1" % (partitionDevicePath) )
		if (0 == int(exitcode)):
			break
		retries += 1
		logger.notice(u"could not find %s - retry" % (partitionDevicePath) )
		if retries == 3:
			logger.debug(u"Forcing kernel to reread the partitiontable again")
			#disk._forceReReadPartionTable()
			exitcode = os.system('%s %s >> /dev/null 2>&1' % (which('partprobe'), diskDevice))
			if not useGpt:
				partitions = disk.getPartitions()
		time.sleep(2)
	exitcode = os.system("test -b %s >> /dev/null 2>&1" % (partitionDevicePath) )
	if (0 != int(exitcode)):
		logger.error(u"could not find %s - giving up" % (partitionDevicePath) )
		scriptMessageSubject.setMessage(u"Error checking %s. partition" % (partitionDevicePath))
		raise Exception(u"Error checking %s. partition" % (partitionDevicePath))
	
	logger.notice(u"%s exists as device - fine" % (partitionDevicePath) )
	dummy = isBlockAlignedPartition(diskDevice, partitionNumber,useGpt)

def createPartitionEx(partitionName = "unknown", partitionNumber = "", partitionLabel = "unknown", startM = 0, partitionSizeM = 0, gptAutoAppend = False, boot = False, gptAttribute = "" , useGpt = False, diskDevice = "", fileSystem = "unknown", gptFileSystem="0000"):
	#	Liste der z.Zt. bekannten Attribute
	#Wert 	Beschreibung
	#0 	Systempartition (system partition)
	#1 	Verstecke die Partition vor EFI (hide from EFI)
	#2 	Legacy Bootflag (legacy BIOS bootable)
	#60 	Nur lesen (read-only)
	#62 	Versteckt (hidden)
	#63 	Nicht Einhaengen (do not automount) 
	#
	# partitionSizeM = -1 = 100% = use the rest of the disk
	partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
	logger.notice(u"Create %s partition on %s start: %sM, size: %sM" % (partitionName, partitionDevicePath, startM, partitionSizeM))
	scriptMessageSubject.setMessage(u"Create %s partition" % partitionName)
	if useGpt:
		if gptAutoAppend:
			if partitionSizeM == -1:
				gptSgdiskParam = "--new %d::" % (partitionNumber)
			else:
				gptSgdiskParam = "--new %d::+%dM" % (partitionNumber, partitionSizeM)
		else:
			if partitionSizeM == -1:
				gptSgdiskParam = "--new %d:%dM:" % (partitionNumber, startM)
			else:
				gptSgdiskParam = "--new %d:%dM:%dM" % (partitionNumber, startM, partitionSizeM)
		if partitionLabel != "unknown":
			gptSgdiskParam = gptSgdiskParam + ' -c %d:\"%s\"' % (partitionNumber, partitionLabel)
		if gptAttribute:
			gptSgdiskParam = gptSgdiskParam + ' --attributes %d:set:%s' % (partitionNumber, gptAttribute)
		if gptFileSystem != "0000":
			gptSgdiskParam = gptSgdiskParam + ' -t %d:%s' % (partitionNumber, gptFileSystem)
		execute('/usr/sbin/sgdisk %s -p %s' % (gptSgdiskParam, diskDevice))
		execute('/bin/sleep 2')
		execute('/usr/sbin/sgdisk -p %s' % (diskDevice))
		# --attributes %d:set:63 --> 63 means: 'no auto mount' and at windows: 'no drive letter'
	else:
		if partitionSizeM == -1:
			endstr = "100%"
		else:
			endstr = "%dM" % (partitionSizeM + startM)
		disk.createPartition(start = "%dM" % startM, end = "%s" % endstr, fs = fileSystem, boot = boot, number = partitionNumber)
		partitions = disk.getPartitions()
	testPartitionEx(diskDevice, partitionNumber , useGpt )
		
def testBlkidEx(diskDevice = "", partitionNumber = "", useGpt = False, partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
	
	# copied from posix.px line2045
	retries = 0
	while retries <= 6:
		#if os.path.exists(disk.getPartition(winpePartitionNumber)['device']):
		# disk do not work with gpt right now
		execute("blkid")
		time.sleep(5)
		exitcode = os.system("blkid %s >> /dev/null 2>&1" % (partitionDevicePath))
		if (0 == int(exitcode)):
			break
		retries += 1
		logger.notice(u"blkid could not find %s - retry" % (partitionDevicePath) )
		if (retries % 2) == 0:
			logger.debug(u"Forcing kernel to reread the partitiontable again")
			#disk._forceReReadPartionTable()
			exitcode2 = os.system('%s %s >> /dev/null 2>&1' % (which('partprobe'), diskDevice))
			execute('%s -p %s' % (which('sgdisk'), diskDevice))
			execute('%s -L --no-reread -l' % which('sfdisk'), captureStderr=False)
			if not useGpt:
				partitions = disk.getPartitions()
		time.sleep(5)
	if (0 != int(exitcode)):
		logger.error(u"blkid could not find %s - giving up" % (partitionDevicePath) )
		scriptMessageSubject.setMessage(u"Error blkid %s. partition" % (partitionDevicePath))
		raise Exception(u"Error blkid %s. partition" % (partitionDevicePath))
	
	logger.notice(u"%s exists as device - fine" % (partitionDevicePath) )

def createFilesystemEx(partitionName = "unknown", partitionNumber = "", partitionLabel = "unknown", fileSystem = "unknown", diskDevice = "", useGpt = False, partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			
	logger.notice(u"Create file system %s on partition %s (%s)" % (fileSystem,partitionName, partitionDevicePath))
	scriptMessageSubject.setMessage(u"Create file system %s on partition %s (%s)" % (fileSystem,partitionName, partitionDevicePath))
	
	#if useGpt:
	mkfsOption = "-F"
	labelOption = "-L"
	if fileSystem == "fat32":
		fileSystem = "vfat"
		mkfsOption = mkfsOption + " 32"
		labelOption = "-n"
	if fileSystem == "ntfs":
		mkfsOption = mkfsOption + " --fast"
	if partitionLabel != "unknown":
		mkfsOption = mkfsOption + ' %s "%s"' % (labelOption, partitionLabel)
	execute('sync')
	time.sleep(10)
	execute('/sbin/mkfs.%s %s %s' % (fileSystem, mkfsOption, partitionDevicePath))
	testBlkidEx(diskDevice, partitionNumber, useGpt,partitionDevicePath)
	#testPartitionEx(diskDevice, partitionNumber , useGpt )
	#else:
	#	disk.createFilesystem(partition = partitionNumber, fs = fileSystem)
	#	testPartitionEx(diskDevice, partitionNumber , useGpt )
	#	os.system("blkid %s%d" % (diskDevice, partitionNumber))
	#	#if (partitionLabel != "unknown") and ((fileSystem == "ext3") or (fileSystem == "ext4")):
	#	#	execute('e2label %s%s %s' % (diskDevice, partitionNumber, partitionLabel))
	#	partitions = disk.getPartitions()
	logger.notice(u"%s created and formated" % (partitionDevicePath) )

def partitionHasLabel(diskDevice = "", partitionNumber = "", partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
	
	partitionLabel = ""
	execute("blkid")
	resultlist = execute(u'blkid -o value -s LABEL %s' % (partitionDevicePath) )
	if not resultlist:
		resultlist = execute(u'blkid -o value -s PARTLABEL %s' % (partitionDevicePath) )
	for resultline in resultlist:
		try:
			partitionLabel = resultline.strip()
		except:
			pass
	logger.notice(u"%s exists as device with label: %s" % (partitionDevicePath, partitionLabel) )
	return partitionLabel
	
def checkCreateDir(targetDir = ""):
	exitcode = os.system("test -d %s >> /dev/null 2>&1" % (targetDir))
	if (0 == int(exitcode)):
		logger.notice(u"%s exists as directory - fine" % targetDir)
	else:
		logger.notice(u"%s does not exists as directory - creating" % targetDir)
		execute("mkdir -p %s" % targetDir)
	exitcode = os.system("test -d %s >> /dev/null 2>&1" % (targetDir))
	if (0 != int(exitcode)):
		raise Exception(u"Could not find or create directory %s" % targetDir)

def checkClearMountpoint(targetDir = "", diskDevice = "", partitionNumber = "", partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
	if os.path.isdir(targetDir):
		logger.notice(u"mountpoint %s exists" % targetDir)
	else:
		logger.notice(u"creating mountpoint %s " % targetDir)
		execute("mkdir -p %s" % targetDir)
		
	logger.notice(u"mountpoint %s >> /dev/null 2>&1" % targetDir)
	exitcode = os.system("mountpoint %s >> /dev/null 2>&1" % (targetDir))
	if (0 == int(exitcode)):
		logger.notice(u"something mounted on %s" % targetDir)
		exitcode = os.system("mount | grep %s | grep %s>> /dev/null 2>&1" % (partitionDevicePath, targetDir) )
		if (0 == int(exitcode)):
			logger.notice(u"%s mounted on %s - fine"  % (partitionDevicePath, targetDir) )
		else:
			exitcode = os.system("umount %s >> /dev/null 2>&1" % (targetDir))
			if (0 == int(exitcode)):
				logger.notice(u"succsseful unmounted %s - fine"  % (targetDir) )
			else:
				logger.notice(u"Could not unmount %s - giving up" % (targetDir) )
				raise Exception(u"Could not unmount %s - giving up" % (targetDir) )
	else:
		logger.notice(u"Nothing mounted on %s - fine" % targetDir)

def checkClearPartition(targetDir = "", diskDevice = "", partitionNumber = "", partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
	
	exitcode = os.system("mount | grep %s >> /dev/null 2>&1" % (partitionDevicePath))
	if (0 == int(exitcode)):
		logger.notice(u"%s is mounted" % (partitionDevicePath))
		exitcode = os.system("mount | grep %s | grep %s>> /dev/null 2>&1" % (partitionDevicePath, targetDir) )
		if (0 == int(exitcode)):
			logger.notice(u"%s mounted on %s - fine"  % (partitionDevicePath, targetDir) )
		else:
			exitcode = os.system("umount %s >> /dev/null 2>&1" % (partitionDevicePath))
			if (0 == int(exitcode)):
				logger.notice(u"succsseful unmounted %s"  % (partitionDevicePath) )
			else:
				logger.notice(u"Could not unmount partition %s - giving up" % (partitionDevicePath) )
				raise Exception(u"Could not unmount partition %s - giving up" % (partitionDevicePath) )
	else:
		logger.notice(u"%s is not mounted" % (partitionDevicePath))
		
def checkMount(targetDir = "", diskDevice = "", partitionNumber = "", fileSystem = "", partitionDevicePath = ""):
	if partitionDevicePath == "":
		if partitionNumber and diskDevice:
			partitionDevicePath = getPartitionDevicePath(diskDevice, partitionNumber)
		else:
			logger.error(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
			raise Exception(u"No partitionDevicePath: pDP: %s , diskDevice: %s , partitionNumber: %s" % (partitionDevicePath, diskDevice, partitionNumber))
	
	execute('sync')
	exitcode = os.system("mount | grep %s | grep %s>> /dev/null 2>&1" % (partitionDevicePath, targetDir) )
	if (0 == int(exitcode)):
		logger.notice(u"%s mounted on %s - fine"  % (partitionDevicePath, targetDir) )
	else:
		if fileSystem != "":
			logger.notice(u" mount -t %s %s %s" % (fileSystem, partitionDevicePath, targetDir) )
			time.sleep(5)
			exitcode = os.system("mount -t %s %s %s" % (fileSystem, partitionDevicePath, targetDir) )
		else:
			logger.notice(u" mount %s %s" % (partitionDevicePath, targetDir) )
			time.sleep(5)
			exitcode = os.system("mount %s %s" % (partitionDevicePath, targetDir) )
		if (0 == int(exitcode)):
			logger.notice(u"%s mounted on %s - fine.." % (partitionDevicePath, targetDir) )
		else:
			logger.notice(u"Failed to mount %s on %s - retry" % (partitionDevicePath, targetDir) )
			execute('sync')
			if fileSystem != "":
				logger.notice(u" mount -t %s %s %s" % (fileSystem, partitionDevicePath, targetDir) )
				time.sleep(5)
				exitcode = os.system("mount -t %s %s %s" % (fileSystem, partitionDevicePath, targetDir) )
			else:
				logger.notice(u" mount %s %s" % (partitionDevicePath, targetDir) )
				time.sleep(5)
				exitcode = os.system("mount %s %s" % (partitionDevicePath, targetDir) )
			if (0 == int(exitcode)):
				logger.notice(u"%s mounted on %s - fine.." % (partitionDevicePath, targetDir) )
			else:
				logger.notice(u"Failed to mount %s on %s - giving up" % (partitionDevicePath, targetDir) )
				raise Exception(u"Failed to mount %s on %s - giving up" % (partitionDevicePath, targetDir) )

def getGptPartitionSizesInMegabytes(device, givenOutput=None):
	"""
	Extracts the size of the partitions from ``device``.

	If ``givenOutput`` exists it will use the data from there.
	Otherwise it will get the data for ``device``.

	:returns: A mapping with the partition number as key and the size in megabytes as value.
	:returntype: dict
	"""
	if givenOutput is None:
		givenOutput = execute(
			'{cmd} -i {device}'.format(
				cmd=which('sgdisk'),
				device=device,
			)
		)

	partitionInfoRegEx = re.compile('^(\d+)\s+(\d+)\s+(\d+)')
	sectorSizeRegex = re.compile('logical sector size:\s*(\d+)\s+bytes')

	sizes = {}
	sectorSize = None
	for line in givenOutput:
		line = line.strip().lower()

		if 'logical sector size' in line:
			sectorSizeMatch = sectorSizeRegex.search(line)
			if sectorSizeMatch:
				sectorSize = int(sectorSizeMatch.group(1))
			else:
				raise ValueError('Unknown sector size unit in line "{0}"'.format(line))

		match = partitionInfoRegEx.search(line)
		if match:
			partitionStart = int(match.group(2))
			partitionEnd = int(match.group(3))
			sectorsUsedByPartition = partitionEnd - partitionStart
			sizes[int(match.group(1))] = sectorsUsedByPartition * sectorSize / (1024**2)

	return sizes

####################################### UEFI FUNCTIONS  #############################################################

def inUefiMode():
	# use 'os.system' to do not break on exitcode != 0
	#useGptOnUefi = False
	logger.notice(u"try to load efivars module: modprobe efivars")
	try:
		execute('/sbin/modprobe efivars')
	except:
		logger.notice(u"we are not running in uefi mode")
		scriptMessageSubject.setMessage(u"we are not running in uefi mode")
		return False
	logger.notice(u"check if we run in uefi mode")
	# use 'os.system' to do not break on exitcode != 0
	efiexitcode = os.system("efibootmgr >> /dev/null 2>&1")
	if (0 == int(efiexitcode)):
		#useGptOnUefi = True
		logger.notice(u"we are running in uefi mode")
		scriptMessageSubject.setMessage(u"we are running in uefi mode")
		return True
	else:
		logger.notice(u"we are not running in uefi mode")
		scriptMessageSubject.setMessage(u"we are not running in uefi mode")
		return False
		
		

# function to delete entries from uefi boot loader by label
# part 1: parsing output from efibootmgr -v
def getIDsOfEntries(searchTerm, output):
	def getIDfromLine(line):
		match = re.search("^Boot(([\dA-F]+))", line)
		return match.group(1)
	return [getIDfromLine(line) for line in output if searchTerm in line and line.startswith("Boot")]
# part 2: The function to delete entries from uefi boot loader by label
def deleteAllEntriesFromEFIBootmgr(term="opsitempwinpe"):
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	for ID in getIDsOfEntries(term, output):
		execute("{bootmgr} -b {hexID} --delete-bootnum".format(bootmgr=bootManager,hexID=ID))
		logger.notice(u"Deleting uefi boot entry %s" % ID)
		
def setNextUefiBoot(term="opsitempwinpe"):
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	for ID in getIDsOfEntries(term, output):
		execute("{bootmgr} -n {hexID}".format(bootmgr=bootManager,hexID=ID))
		logger.notice(u"Set uefi boot entry %s for next boot" % ID)


def getBootOrder(output):
	"""
	Return the boot order.

	The boot order consists of the ID of the entries.

	:rtype: (str, )
	"""
	def splitBootOrderEntries(line):
		return tuple(line.split(','))

	for line in output:
		searchMatch = re.search("^BootOrder:\s+(.*)", line.strip())
		if searchMatch:
			return splitBootOrderEntries(searchMatch.group(1))

	raise Exception('Could not detect boot order!')


def setFirstUefiBoot(label):
	""""
	Set the first UEFI boot entry with the given label.

	:param label: The label of the item that should be first.
	:type label: str
	:raise RuntimeError: If no entry with a matching label is found.
	"""
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	
	for ID in getIDsOfEntries(label, output):
		labelID = ID
	logger.notice('Boot entry %s has ID: %s.' % (label,labelID))

	#nextFirstEntry = None
	#for line in output:
	#	item = getInfoFromLine(line)
	#	if not item:
	#		continue
  #
	#	if item['label'] == entry.strip():
	#		nextFirstEntry = entry
	#		break
	#else:
	#	raise RuntimeError("Missing entry {!r}".format(entry.strip()))

	# get actual boot order list
	newOrder = list(getBootOrder(output))
	try:
		# remove entry set should be set to first
		#indexToDelete = newOrder.index(nextFirstEntry['entry'])
		indexToDelete = newOrder.index(labelID)
		del newOrder[indexToDelete]
	except (IndexError, ValueError):  # Item not in list
		pass

	# set entry to first place in the list
	#newOrder.insert(0, nextFirstEntry['entry'])
	newOrder.insert(0, labelID)

	bootOrder = ','.join(newOrder)
	logger.notice('New bootorder: %s .' % (bootOrder))
	#write back the new boot order
	execute("{cmd} -o {order}".format(cmd=bootManager, order=bootOrder))


def getBootCurrent(output):
	def splitBootOrderEntries(line):
		return tuple(line.split(','))

	for line in output:
		searchMatch = re.search("^BootCurrent:\s+(.*)", line.strip())
		if searchMatch:
			return splitBootOrderEntries(searchMatch.group(1))

	raise Exception('Could not detect current boot!')


def getInformationFromEntry(entryLine):
	def getLoaderInformationFromParameters(param):
		# Searching for all dev(value) pairs
		match = re.findall('(\w+)\((.*?)\)', param)

		values = {}
		for (dev, value) in match:
			if ',' in value:
				values[dev] = tuple(value.split(','))
			else:
				values[dev] = value

		if not values:
			raise Exception('Could not read parameters from: {0}'.format(param))

		return values

	match = re.search("^Boot(?P<entry>[\dA-F]+)\*{0,1} (?P<label>.*)\t+(?P<parameters>.*)", entryLine)

	if match:
		result = {
				'entry': match.group('entry'),
				'label': match.group('label').strip()
			}

		parameters = match.group('parameters')

		if '(' in parameters and ')' in parameters:
			result['parameters'] = getLoaderInformationFromParameters(parameters.strip())
		else:
			result['parameters'] = {'device': parameters.strip()}

		return result


def getInfoFromLine(ID, output):
	for line in output:
		if line.strip().startswith("Boot{id}".format(id=ID)):
			return getInformationFromEntry(line)

	logger.error("Can't find entry with ID '{0}'".format(ID))


def uefiShowEntriesByBootOrder():
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	bootOrder = getBootOrder(output)

	for ID in bootOrder:
		info = getInfoFromLine(ID, output)
		logger.notice('Information from boot entry {1}: {0}'.format(info, ID))

	#firstEntry = bootOrder[0]
	#info = getInfoFromLine(firstEntry, output)
  #
	#logger.notice('First boot entry: {0}'.format(info['label']))
	#if 'HD' in info['parameters']:
	#	logger.notice('Partition: {0}'.format(info['parameters']['HD'][0]))
	#	logger.notice('Loader: {0}'.format(info['parameters']['File']))

def uefiGetFirstBootEntry():
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	firstEntry = getBootOrder(output)[0]
	info = getInfoFromLine(firstEntry, output)
	return info

def uefiGetActBootEntry():
	bootManager = which("efibootmgr")
	output = execute("{0} -v".format(bootManager))
	firstEntry = getBootCurrent(output)[0]
	info = getInfoFromLine(firstEntry, output)
	return info
	
####################################### local-image FUNCTIONS  #############################################################
def getDiskIndexFromMultiDiskMode(multiDiskMode = 0):
	disks = getHarddisks()
	disks = sorted(disks, key=lambda disk: disk.device)
	diskindex = 0
	if (len(disks) > 1):
		logger.notice(u"We have more than one disk: %d disks - looking for multi_disk_mode" % (len(disks)))
		if (multiDiskMode == "1"):
			diskindex = 1
		if (multiDiskMode == "2") and (len(disks) >= 3):
			diskindex = 2
		if (multiDiskMode == "3") and (len(disks) >= 4):
			diskindex = 3
		if (multiDiskMode == "prefer_ssd"):
			for disknum in range(len(disks)-1,0,-1):
				if not isRotationalDisk(disks[disknum].device):
					diskindex = disknum
		if (multiDiskMode == "prefer_rotational"):
			for disknum in range(len(disks)-1,0,-1):
				if isRotationalDisk(disks[disknum].device):
					diskindex = disknum
			
		logger.notice(u"dual_disk_mode is %s - so we use disk %d" %(multiDiskMode,diskindex))
	return diskindex

def getBackupdiskindexFromBackupPartitionOnSameDisk(backup_partition_on_same_disk = True):
	backupPartitionNumber = 0
	if (backup_partition_on_same_disk == False) and (len(disks) == 1):
		logger.warning(u"backup_partition_on_same_disk was false but we only one disk - so we ignore this property")
		backup_partition_on_same_disk = True
	if (backup_partition_on_same_disk == False) and (len(disks) > 1):
		if (diskindex == 0):
			backupdiskindex = 1
		else:
			backupdiskindex = 0
		logger.notice(u"backup_partition_on_same_disk = False - so we use for backup disk %d" % (backupdiskindex))
	if (backup_partition_on_same_disk == True):
		backupdiskindex = diskindex
	return backupdiskindex, backup_partition_on_same_disk

	
def checkOliPartitions(diskindex = 0, backupdiskindex = 0,useGpt = False,backup_partition_on_same_disk = True):
	global systemPartitionNumber
	global winpePartitionNumber
	global backupPartitionNumber
	global dataPartitionNumber
	mylocaldataPartitionNumber = dataPartitionNumber
	
	disk = disks[diskindex]
	if not useGpt:
		# Get current partitions
		partitions = disk.getPartitions()
		if not partitions:
			# No partition found on harddisk
			scriptMessageSubject.setMessage(u"Found no partitions on %s " % disk.device)
			scriptMessageSubject.setMessage(u"No partitions - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
			
			raise Exception(u"No partitions - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
	try:	
		mylocaldataPartitionNumber = 0
		testPartitionEx(disk.device, systemPartitionNumber, useGpt)
		partitionLabel = partitionHasLabel(disk.device, systemPartitionNumber,getPartitionDevicePath(disk.device, systemPartitionNumber))
		logger.notice(u"%s has label %s" % (getPartitionDevicePath(disk.device, systemPartitionNumber),partitionLabel))
		if (partitionLabel.lower() == "windows") or (partitionLabel.lower() == "system") or (partitionLabel.lower() == ""):
			logger.notice(u"%s exists as expected - fine" % (getPartitionDevicePath(disk.device, systemPartitionNumber)) )
		else:
			logger.error(u"%s exists not as expected with label SYSTEM - not ok - giving up" % (getPartitionDevicePath(disk.device, systemPartitionNumber)) )
			scriptMessageSubject.setMessage(u"%s exists not as expected with label SYSTEM - not ok - giving up" % (getPartitionDevicePath(disk.device, systemPartitionNumber)) )
			raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
		
		testPartitionEx(disk.device, winpePartitionNumber, useGpt)
		partitionLabel = partitionHasLabel(disk.device, winpePartitionNumber,getPartitionDevicePath(disk.device, winpePartitionNumber))
		logger.notice(u"%s has label %s" % (getPartitionDevicePath(disk.device, winpePartitionNumber),partitionLabel))
		if (partitionLabel.lower() == "swap") or (partitionLabel.lower() == "winpe") or (partitionLabel.lower() == ""):
			logger.notice(u"%s exists as expected - fine" % (getPartitionDevicePath(disk.device, winpePartitionNumber)))
		else:
				if (partitionLabel.lower() == 'sysdata') or (partitionLabel.lower() == 'data'):
					mylocaldataPartitionNumber = 2
					if useGpt:
						mylocaldataPartitionNumber += 2
					winpePartitionNumber += 1
					logger.notice(u"%s%s exists as expected at 4 partions with label %s - checking next partition" % (disk.device, mylocaldataPartitionNumber, partitionLabel))
					dataPartitionNumber = mylocaldataPartitionNumber
				else:
					logger.error(u"%s exists not as expected with label data/sysdata/swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, winpePartitionNumber)) )
					scriptMessageSubject.setMessage(u"%s exists not as expected with label data/sysdata/swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, winpePartitionNumber)) )
					raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
	
		testPartitionEx(disk.device, winpePartitionNumber, useGpt)
		partitionLabel = partitionHasLabel(disk.device, winpePartitionNumber,getPartitionDevicePath(disk.device, winpePartitionNumber))
		logger.notice(u"%s has label %s" % (getPartitionDevicePath(disk.device, winpePartitionNumber),partitionLabel))
		if (partitionLabel.lower() == "swap") or (partitionLabel.lower() == "winpe") or (partitionLabel.lower() == ""):
			logger.notice(u"%s exists as expected - fine" % (getPartitionDevicePath(disk.device, winpePartitionNumber)) )
		else:
			logger.error(u"%s exists not as expected with label swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, winpePartitionNumber)) )
			scriptMessageSubject.setMessage(u"%s exists not as expected with label swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, winpePartitionNumber)) )
			raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
		
	except:
		raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
	
	disk = disks[backupdiskindex]
	logger.notice(u"Change to backup disk with index: %d - Device name%s" % (backupdiskindex,disk.device))
	if not useGpt:
		# Get current partitions
		partitions = disk.getPartitions()
		if not partitions:
			# No partition found on harddisk
			scriptMessageSubject.setMessage(u"Found no partitions on %s " % disk.device)
			scriptMessageSubject.setMessage(u"No partitions - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
			
			raise Exception(u"No partitions - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
	try:
		#dataPartitionNumber = 0
		testPartitionEx(disk.device, backupPartitionNumber, useGpt)
		partitionLabel = partitionHasLabel(disk.device, backupPartitionNumber,getPartitionDevicePath(disk.device, backupPartitionNumber))
		logger.notice(u"%s has label %s" % (getPartitionDevicePath(disk.device, backupPartitionNumber),partitionLabel))
		if (partitionLabel.lower() == "opsidata"):
			logger.notice(u"%s exists as expected - fine" % (getPartitionDevicePath(disk.device, backupPartitionNumber)) )
		else:
			if (partitionLabel.lower() == 'swap') or (partitionLabel.lower() == 'winpe') or (partitionLabel.lower() == 'data'):
				logger.notice(u"%s exists as expected at 4 partions with label %s - checking next partition" % (getPartitionDevicePath(disk.device, backupPartitionNumber), partitionLabel))
				backupPartitionNumber += 1
				if (mylocaldataPartitionNumber == 0):
					mylocaldataPartitionNumber = 2
					if useGpt:
						mylocaldataPartitionNumber += 2
					winpePartitionNumber += 1
					dataPartitionNumber = mylocaldataPartitionNumber
			else:
				logger.error(u"%s exists not as expected with label opsidata/swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, backupPartitionNumber)) )
				scriptMessageSubject.setMessage(u"%s exists not as expected with label opsidata/swap/winpe/'' - not ok - giving up" % (getPartitionDevicePath(disk.device, backupPartitionNumber)) )
				raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
		
		
		if (dataPartitionNumber >= 2):
			testPartitionEx(disk.device, backupPartitionNumber, useGpt)
			partitionLabel = partitionHasLabel(disk.device, backupPartitionNumber,getPartitionDevicePath(disk.device, backupPartitionNumber))
			logger.notice(u"%s has label %s" % (getPartitionDevicePath(disk.device, backupPartitionNumber),partitionLabel))
			if (partitionLabel.lower() == "opsidata"):
				logger.notice(u"%s exists as expected - fine" % (getPartitionDevicePath(disk.device, backupPartitionNumber)) )
				logger.notice("Partition numbers are now: system=%d, data=%s, swap=%d, backup=%d" % (systemPartitionNumber, dataPartitionNumber, winpePartitionNumber, backupPartitionNumber))
			else:
				logger.Error(u"%s exists not as expected with label %s - not ok - giving up" % (getPartitionDevicePath(disk.device, backupPartitionNumber), backupPartitionLabel) )
				scriptMessageSubject.setMessage(u"%s exists not as expected with label %s - not ok - giving up" % (getPartitionDevicePath(disk.device, backupPartitionNumber), backupPartitionLabel) )
				raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")
	except:
		raise Exception(u"Wrong partition table - Please run the opsi product 'opsi-local-image-prepare' to prepare this disk ! ")

####################################### MISC FUNCTIONS  #############################################################

def waitForFile(filename):

    for count in range(20):
        if os.path.exists(filename):
            return
        else:
            time.sleep(1)
    raise IOError(u"File {} does not exist".format(filename))

def getArchitecture():
	myplatform = platform.machine()
	if myplatform in ['x86_64', 'AMD64', 'amd64']:
		logger.notice("64 Bit system....")
		return 'amd64'
	else:
		logger.notice("32 Bit system....")
		return 'i386'

def doChrooted(root, cmds, proxy):
	f = open( root + '/tmp/doit.sh', 'w')
	if proxy:
		logger.notice("Configuring proxy")
		print >> f,"export http_proxy=%s" % proxy
		print >> f,"export https_proxy=%s" % proxy
	for cmd in cmds:
		print >> f, cmd
	f.close()
	execute("chroot %s /bin/bash /tmp/doit.sh" % root)
	
def checkModules(module2check):
	# Check modules file
	logger.notice(u"Modules file check....")
	try:
		modules = None
		helpermodules = {}
		## backendinfo = self._configService.backend_info()
		backendinfo = backend.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']
		logger.notice(u"Modules file loaded....")
		if not modules.get(module2check):
			raise Exception(u"%s not available - module currently disabled" % module2check)
		if not modules.get('customer'):
			raise Exception(u"%s not available - no customer set in modules file" % module2check)
		if not modules.get('valid'):
			raise Exception(u"%s not available - modules file invalid" % module2check)
		if (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
			raise Exception(u"%s not available - modules file expired" % module2check)
		logger.notice(u"Modules file check 1 passed....")
	
		publicKey = keys.Key.fromString(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''
		mks = modules.keys()
		mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue
			if helpermodules.has_key(module):
				val = helpermodules[module]
				if int(val) > 0:
					modules[module] = True
			else:
				val = modules[module]
				if (val == False): val = 'no'
				if (val == True):  val = 'yes'
			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ])):
			raise Exception(u"%s not available - modules file invalid" % module2check)
		logger.notice(u"Modules file signature verified (customer: %s)" % modules.get('customer'))
	except Exception, e:
		raise

###
def handle_win_setupAfterInstall():
	setupAfterInstall = productPropertyValues.get('setup_after_install', '')
	if setupAfterInstall:
		for setupProduct in setupAfterInstall:
			setupProduct = setupProduct.strip()
			if u',' in setupProduct:
				# This is the workaround for a bug where the list of
				# images will become a comma-seperated string instead of
				# a list of strings.
				for key_part in setupProduct.split(u','):
					if not (key_part in setupAfterInstall):
						setupAfterInstall.append(key_part)
				setupAfterInstall.remove(setupProduct)
				backend.productPropertyState_create(productId = productId ,propertyId = 'setup_after_install',objectId = clientId,values = setupAfterInstall)
		for setupProduct in setupAfterInstall:
			setupProduct = setupProduct.strip()
			if setupProduct != '':
				logger.notice(u"Set to setup %s" % (setupProduct) )
				backend.setProductActionRequestWithDependencies(productId=setupProduct, clientId=clientId, actionRequest='setup')
# end of handle_win_setupAfterInstall

def getBroadcastAddress(ipAddress, netmask):
	return u".".join(u"%d" % (int(ipAddress.split(u'.')[i]) | int(netmask.split(u'.')[i]) ^255) for i in range(len(ipAddress.split('.'))))

def getNetworkAddress(ipAddress, netmask):
	return u".".join(u"%d" % (int(ipAddress.split(u'.')[i]) & int(netmask.split(u'.')[i])) for i in range(len(ipAddress.split('.'))))

################ end local def #################################################################################

