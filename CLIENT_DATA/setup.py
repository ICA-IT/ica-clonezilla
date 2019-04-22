# This code is based on part of the opsi.org project
# http://opsi.org
#
# original based on code that is copyrighted and owned by uib, i.e.:
# Copyright (c) uib gmbh (www.uib.de)
# This sourcecode is owned by the uib gmbh, D55118 Mainz, Germany
# and published under the Terms of the GNU Affero General Public License.
# Text of the AGPL: http://www.gnu.org/licenses/agpl-3.0-standalone.html
# credits: http://www.opsi.org/credits/
# 
# All modifications of re-named version (ica-clonezilla) are public domain

#***************************************************************************
# Subversion:
# $Revision: 1 $
# $Author: John Kuras $
# $Date: 2018-10-16  $
#***************************************************************************

# opsi - clonezilla integration
# download from:
# http://free.nchc.org.tw/drbl-core/src/unstable/
# http://free.nchc.org.tw/drbl-core/src/stable/
# Steps:
# 1. extract on linux system
# 2. change dir into clonezilla dir
# 3. create destdir directory
# 4. edit Makefile: set destdir ; Example:
#    DESTDIR = /home/tmp_neu/detlef/clonezilla-3.10.11/destdir
# 5. run: make all ; make install
# 6. change into destdir
# 7. set rights:
#    chown -R root:root *
#    chmod -R 755 *
# 8. create tgz file for opsi: go to destdir and:
#    tar zcvf ../clonezilla-3.10.11.tgz .
# 9. copy clonezilla.tgz to the lib directory of this product
# 10. do the same for drbl*.tar.bz2

# integration of partclone
# download from http://sourceforge.net/projects/partclone/files/stable/0.2.80/
# e.g. http://sourceforge.net/projects/partclone/files/stable/0.2.80/partclone_0.2.80-1_i386.deb/download
# extract deb file - you will get a data.tar
# extract data.tar on a linux fs (to conserve symbolic links and access rights):
# mkdir tmp
# cd tmp
# tar xvf ../data.tar
# tar cvzf ../partclone-0.2.80.tgz .

# partclone-0.2.69 -> trusty ntfs-3g (849)
# partclone-0.2.80 -> vivid ntfs-3g (853)


#
# This script requires opsi >= 4.0, opsi-linux-bootimage version >= 20150727
#
#raw_input('Press Enter1')
if not bootimageVersion or (int(bootimageVersion) < 20160517):
	raise Exception(u"This product requires opsi-linux-bootimage version >= 20160517")
try:
	if not backend.backend_info()['opsiVersion'].startswith('4.'):
		raise ValueError('No opsi 4.x backend present')
except Exception:
	raise Exception(u"This is a opsi 4.x product")

from socket import getfqdn
from urlparse import urlparse

#include opsi setup library
depot.copy(SCRIPT_PATH+'/opsisetuplib.py','/tmp')
execfile('/tmp/opsisetuplib.py')

initOpsiSetupLib()
result = execute("free -m")

# give credits
ui.showMessage("Credits to Clonezilla \nThe Free and Open Source Software for Disk Imaging and Cloning \nhttp://clonezilla.org/ \n", title="opsi-Clonezilla", seconds=5)

# load clonezilla, drbl, and perl after cifs mount to avoid network resolution problem

mountImageShare = True
if (str(productProperties.get('mount_image_share', 'true')).lower() == 'false'):
	mountImageShare = False

imageshare = productProperties.get('imageshare', 'auto')
logger.notice(u"got imageshare value: %s " % (imageshare))
if (imageshare == '') or (imageshare.lower() == 'auto'):
	depotId = backend.getDepotId(clientId=clientId)
	#logger.notice(u"depotId is : %s" % depotId)
	depotHash = backend.getDepot_hash(depotId=depotId)
	#logger.notice(u"depotHash is : %s" % depotHash)
	depotRemoteUrl = depotHash["depotRemoteUrl"]
	logger.notice(u"depotRemoteUrl is : %s" % depotRemoteUrl)
	myurlparser = urlparse(depotRemoteUrl)
	servername = myurlparser.hostname
	imageshare = "//%s/opsi_images" % servername
	logger.notice(u"imageshare was empty or auto and is set to: %s" % imageshare)
imagefile = productProperties.get('imagefile', 'myimagefile')
if imagefile == 'auto':
    imagefile = getfqdn()
logger.notice(u"got imagefile value: %s " % (imagefile))
runcommand = productProperties.get('runcommand', '/sbin/ocs-live')
logger.notice(u"got runcommand value: %s " % (runcommand))
runcommand = runcommand.strip()
disk_number = productProperties.get('disk_number', '1')
try:
	disk_num_int = int(disk_number) -1
except:
	logger.error(u"Error: Given disk_number %s is no Integer- giving up" % (disk_number) )
	scriptMessageSubject.setMessage(u"Error: Given disk_number %s is no Integer- giving up" % (disk_number) )
	raise Exception(u"Error: Given disk_number %s is no Integer- giving up" % (disk_number) )
part_number = productProperties.get('part_number', '1')
try:
	part_num_int = int(part_number)
except:
	logger.error(u"Error: Given part_number %s is no Integer- giving up" % (part_number) )
	scriptMessageSubject.setMessage(u"Error: Given part_number %s is no Integer- giving up" % (part_number) )
	raise Exception(u"Error: Given part_number %s is no Integer- giving up" % (part_number) )

# Get harddisks
disks = getHarddisks()
disks = sorted(disks, key=lambda disk: disk.device)
# get diks
disk = disks[disk_num_int]
diskdevicepath = disk.device
partdevicepath = getPartitionDevicePath(disk.device, part_number)
# clonezilla do not like the complete device path
diskdevicepath = diskdevicepath.replace('/dev/', '')
partdevicepath = partdevicepath.replace('/dev/', '')
logger.notice(u"Using as diskdevicepath: %s " % (diskdevicepath))
logger.notice(u"Using as partdevicepath: %s " % (partdevicepath))


mountpoint = '/home/partimag'
logger.notice(u"using mountpoint value: %s " % (mountpoint))


if mountImageShare:
	logger.notice(u"will mount share %s to %s" % (imageshare,mountpoint))
	ui.getMessageBox().addText(u"will mount share%s to %s \n" % (imageshare,mountpoint))
	share=imageshare
	goOn = True
	# mount the image (backup) file system
	# check the mount point
	exitcode = os.system("test -d %s >> /dev/null 2>&1" % (mountpoint))
	if (0 == int(exitcode)):
		logger.notice(u"%s exists as directory - fine" % mountpoint)
	else:
		logger.notice(u"%s does not exists as directory - creating" % mountpoint)
		os.makedirs(mountpoint)
		#os.system("mkdir %s" % (mountpoint))

	# check if mount point is in use
	if goOn:
		logger.notice(u"mountpoint %s >> /dev/null 2>&1" % mountpoint)
		exitcode = os.system("mountpoint %s >> /dev/null 2>&1" % (mountpoint))
		if (0 == int(exitcode)):
			logger.notice(u"something mounted on %s" % mountpoint)
			exitcode = os.system("mount | grep %s | grep %s>> /dev/null 2>&1" % (share, mountpoint) )
			if (0 == int(exitcode)):
				logger.notice(u"%s mounted on %s - fine"  % (share, mountpoint) )
			else:
				exitcode = os.system("umount %s >> /dev/null 2>&1" % (mountpoint))
				if (0 == int(exitcode)):
					logger.notice(u"succsseful unmounted %s"  % (mountpoint) )
				else:
					logger.notice(u"could not unmount %s - giving up" % (mountpoint) )
					goOn = False
		else:
			logger.notice(u"nothing mounted on %s" % mountpoint)
	
	servername = ''
	lines = []
	#depotRemoteUrl = configStates.get('depotRemoteUrl', [''])[0]
	myurlparser = urlparse(imageshare)
	servername = myurlparser.hostname
	logger.notice(u"servername is: %s" % servername)
	shareusername = configStates.get('clientconfig.depot.user', ['%s\\pcpatch'% servername])[0]
	logger.notice(u"shareusername is: %s" % shareusername)
	domainname = shareusername.split('\\')[0]
	if shareusername.split('\\').count > 1:
		username = shareusername.split('\\')[1]
	else:
		# no domain given
		username = domainname
		domainname = ''
	#options = { u'username' : shareusername.split("\")[0], u'password' : pcpatchPassword , u'iocharset':u'utf8' }
	#for (key, value) in options.items():
	#	options[key] = forceUnicode(value)
	#	logger.notice('key=%s ,value=%s' % (key,value))
	lines.append("%s=%s" % ('username',username))
	lines.append("%s=%s" % ('domainname',domainname))
	lines.append("%s=%s" % ('password',pcpatchPassword))
	lines.append("%s=%s" % ('iocharset','utf8'))
	#writing file
	credentialsfilename = "/tmp/cred%s" % os.getpid()
	credentialsfile = TextFile(credentialsfilename)
	credentialsfile.open(mode="wb")
	credentialsfile.writelines(lines)
	credentialsfile.close()
	#execute('cat %s' % credentialsfilename)
	optString = u'-o credentials=%s' % credentialsfilename
	#optString = u''
	#for (key, value) in options.items():
	#	key   = forceUnicode(key)
	#	value = forceUnicode(value)
	#	if value:
	#		optString += u',%s=%s' % (key, value)
	#	else:
	#		optString += u',%s' % key
	#if optString:
	#	optString = u'-o "%s"' % optString[1:].replace('"', '\\"')
	try:
		result = execute(u"%s %s %s %s" % (which('mount.cifs'), imageshare, mountpoint, optString))
		os.remove(credentialsfilename)
	except:
		try:
			optString = u'-o "vers=1.0,credentials=%s"' % credentialsfilename
			result = execute(u"%s %s %s %s" % (which('mount.cifs'), imageshare, mountpoint, optString))
			os.remove(credentialsfilename)
		except:
			os.remove(credentialsfilename)
			raise
	result = execute("ls -l %s" % mountpoint)
else:
        # check the mount point
        exitcode = os.system("test -d %s >> /dev/null 2>&1" % (mountpoint))
	goOn = True
        if (0 == int(exitcode)):
                logger.notice(u"%s exists as directory - fine" % mountpoint)
        else:
                logger.notice(u"%s does not exists as directory - creating" % mountpoint)
                os.makedirs(mountpoint)
                #os.system("mkdir %s" % (mountpoint))

        # check if mount point is in use
        if goOn:
                logger.notice(u"mountpoint %s >> /dev/null 2>&1" % mountpoint)
                exitcode = os.system("mountpoint %s >> /dev/null 2>&1" % (mountpoint))
                if (0 == int(exitcode)):
                        logger.notice(u"something mounted on %s" % mountpoint)
                        exitcode = os.system("mount | grep %s | grep %s>> /dev/null 2>&1" % (share, mountpoint) )
                        if (0 == int(exitcode)):
                                logger.notice(u"%s mounted on %s - fine"  % (share, mountpoint) )
                        else:
                                exitcode = os.system("umount %s >> /dev/null 2>&1" % (mountpoint))
                                if (0 == int(exitcode)):
                                        logger.notice(u"succsseful unmounted %s"  % (mountpoint) )
                                else:
                                        logger.notice(u"could not unmount %s - giving up" % (mountpoint) )
                                        goOn = False
                else:
                        logger.notice(u"nothing mounted on %s" % mountpoint)

        # mount the image (backup) file system
	result = execute("mount %s %s" % imageshare, mountpoint)
#	result = execute("mount /dev/sda3 /home/partimag")

#########################################################
# share mounted - now load the libs
logger.notice(u"Loading libs to execute opsi-clonezilla")
ui.getMessageBox().addText(u"Loading libs to execute opsi-clonezilla \n")

try:
	result = execute("%s" % which(uname -p))
	if result:
		if result[0].strip() == "x86_64":
			arch = "x86_64"
		else:
			arch = "x86"
except Exception as e:
	arch = "x86"

logger.notice(u"Loading perl libs")
ui.getMessageBox().addText(u"Loading perl libs \n")

source = SCRIPT_PATH
target = "/tmp"
pathToPerl = os.path.join(source, "lib", "perl_%s.tgz" % arch)
depot.copy(pathToPerl, target)
pathToPerl = os.path.join(target, "perl_%s.tgz" % arch)

logger.notice(u"Extracting perl")
execute("cd / ; tar xvf %s" % pathToPerl)


logger.notice(u"Extracting and installing clonezilla")
ui.getMessageBox().addText(u"Extracting and installing clonezilla\n")
logger.notice(u"Extract clonezilla")
clonezillapkg = "clonezilla-3.27.16.tgz"
pathToPkg = os.path.join(source, "lib", clonezillapkg)
depot.copy(pathToPkg, target)
pathToPkg = os.path.join(target, clonezillapkg)
execute("cd / ; tar xzvf %s" % pathToPkg)
execute("rm %s" % pathToPkg)

logger.notice(u"Extract drbl")
drblpkg = "drbl-2.25.10.tgz"
pathToPkg = os.path.join(source, "lib", drblpkg)
depot.copy(pathToPkg, target)
pathToPkg = os.path.join(target, drblpkg)
execute("cd / ; tar xzvf %s" % pathToPkg)
execute("rm %s" % pathToPkg)


logger.notice(u"Using builtin partclone")
ui.getMessageBox().addText(u"Using builtin partclone\n")
############################################################
# Patch drbl-ocs.conf
newOptionList = []
pps = backend.productPropertyState_getObjects(objectId=clientId, productId=productId, propertyId='drbl_ocs_conf')
if pps:
	for state in pps:
		newOptionList = state.getValues()

	logger.debug(u"drbl_ocs_conf is: {0}".format([p.toJson() for p in pps]))
logger.debug(u"newOptionList is: {0}".format(newOptionList))

#raw_input('Press Enter5')

filename = '/etc/drbl/drbl-ocs.conf'
logger.notice(u"Setting %s" % filename)

textfile = TextFile(filename)
modified = False
found = False

lines = textfile.readlines()

for option in newOptionList:
	#setting option from MultiValue ProductProperty
	if "=" not in option:
		logger.debug(u'No "=" found in "{0}": skipping')
		continue

	logger.notice(u"Setting %s" % option)
	newOption = option.split("=")[0].strip()
	newValue = option.split("=")[1].strip()
	
	found = False

	for i in range(len(lines)):
		line = lines[i]
		if line.startswith('#') or line.startswith(';'):
			#comment line, skipping
			continue

		if newOption == line.split("=")[0].strip():
			logger.notice(u"Found old value %s" % lines[i])
			lines[i] = '%s=%s' % (newOption, newValue)
			logger.notice(u"Set new value %s" % lines[i])
			if not modified: 
				modified = True

			found = True
			break

	if not found:
		#new option to add
		lines.append('%s=%s' % (newOption, newValue))
		logger.notice(u"Not found - append new value %s" % lines[-1])
		if not modified: 
			modified = True

if modified:
	#build cleaned lines-list
	lines = [line.strip() for line in lines]
	logger.debug("Writing modified file '{0}' with content: {1}".format(filename, '\n'.join(lines)))

	#writing file
	textfile.open(mode="wb")
	textfile.writelines(lines)
	textfile.close()

#logger.notice(u"New: %s" % filename)
#execute("cat %s" % filename)
#raw_input('Press Enter5')
ui.exit()
	
if runcommand != '':
	runcommand = runcommand.replace('imagefile', '%s' % imagefile)
	runcommand = runcommand.replace('diskdevice', '%s' % diskdevicepath)
	runcommand = runcommand.replace('partdevice', '%s' % partdevicepath)

	#runcommand += u' | tee /tmp/clonezilla.log'
	logger.notice(u"Starting runcommand: %s" % runcommand)
	runcommand.encode('utf-8')
	os.system(runcommand)
	#logger.notice(u"ls -lrt /var/log : ")
	#execute("ls -lrt /var/log")
	logger.notice(u"Here starts the clonezilla log:")
	logger.notice(u"------------------------------")
	execute('cat /var/log/clonezilla.log')
	logger.notice(u"------------------------------")
	logger.notice(u"Here ends the clonezilla log")
	#logger.notice(u"Here starts the partclone log:")
	#logger.notice(u"------------------------------")
	#execute('cat /var/log/partclone.log')
	#logger.notice(u"------------------------------")
	#logger.notice(u"Here ends the partclone log")
	
# catch last /tmp/ocs* command and store it in property

setupAfterInstall = productPropertyValues.get('setup_after_install', '')
if setupAfterInstall:
	for setupProduct in setupAfterInstall:
		setupProduct = setupProduct.strip()
		if setupProduct != '':
			logger.notice(u"Set to setup %s" % (setupProduct) )
			backend.setProductActionRequestWithDependencies(productId=setupProduct, clientId=clientId, actionRequest='setup')

# Set product installation status
productOnClient.setInstallationStatus('installed')
productOnClient.setActionProgress('')
productOnClient.setActionResult('successful')
productOnClient.setLastAction('setup')

rebootflag = str(productProperties.get('rebootflag', 'reboot')).lower()
if rebootflag == 'keepalive': 
	logger.notice(u"keepalive")
elif rebootflag == 'shutdown':
	execute('/sbin/shutdown -h now')
else:
	reboot()
