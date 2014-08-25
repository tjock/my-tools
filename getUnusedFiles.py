#!/usr/bin/python

'''
Created on 2013-7-4

@author: tangliuxiang
'''
import re
import os
import subprocess
import sys
import tempfile
import datetime
import multiprocessing
import zipfile
import shutil
import time

HOME = os.path.expanduser('~')
gUnusedKeys = []

THREAD_NUM = 4
OUT_FILE_NAME = "vendor.remove.mk"
OPEN_FILES_NUM_PER_THREAD = 100
gTargetIdx = 0
gTotalTargetNum = 0
frameworkApks = []

DECODE_ALL = "decode_all"
IDTONAME = "idtoname"
APKTOOL = "apktool"
sys.path.append("%s/tools/formatters" % os.environ["PORT_ROOT"])
import idtoname

SAVED_TAGS = {'LIB':['.ko', '/hw/', 'Omx', 'omx', 'stagefright', 'chromatix', 'ril', 'EGL', 'egl', 'Egl', 'GLES', 'mode'],
              'ETC':['permissions', 'firmware', 'module', 'security', 'module', 'dhcpcd', 'blue', 'wifi', 'gps', 'Gps', 'wifi', 'Wifi'],
              'DRAWABLE':['/framework-res-yi/', '/framework-res/']}

REMOVE_DIRS = ["META", "META-INF", "system/etc/security"]

def replaceConflictStr(string):
    return string.replace(r'+', r'\+')

def grepThreadRun(rule, ndGrepFName, outQueue, tName, keyQueue, printLock, suffixGrepCmd=""):
    tmpFileName = tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1]
    tmpFile = file(tmpFileName, 'r+')
    while True:
        printLock.acquire()
#        print "%s, get qsize" % tName
        if keyQueue.empty():
            printLock.release()
            print "%s, EMPTY" % tName
            break
#        print "%s, not empty" % tName
        try:
            target = keyQueue.get(block=False)
        except:
            printLock.release()
            print "%s: queue is empty" % tName
            break

        print "# %s : remaining %s" % (tName, keyQueue.qsize())
        printLock.release()

        fullPath = target[0]

        if fullPath == "":
            continue

        ruleStr = "%s" % replaceConflictStr(target[1])
        for key in target[2:]:
            ruleStr = "%s|%s" % (ruleStr, rule % replaceConflictStr(key))

        tmpFile.seek(0, 0)
        tmpFile.truncate()

        commandStr = 'grep -v "%s" "%s"| xargs egrep -m 1 "%s" -sw %s' % (fullPath, ndGrepFName, ruleStr, suffixGrepCmd)
        # print "# %s commandStr: %s" % (tName, commandStr)
        output = os.popen(commandStr)
        result = output.read()
        if len(result) == 0:
            printLock.acquire()
            print "# %s: can not found %s" % (tName, fullPath)
            printLock.release()
            outQueue.put(fullPath)

class multiGrep:
    def __init__(self, listFileName, notFoundTags, threadNum=THREAD_NUM):
        self.listFileName = listFileName

        unusedTargets = self.getUnusedTargetsList()
        self.unusedKeys = self.getGrepKeys(unusedTargets)

        self.rule = self.getGrepRule()
        self.suffixGrepCmd = self.getSuffixGrepCmd()

        self.threadNum = threadNum
        self.notFoundTags = notFoundTags

        self.ndGrepFName = self.getNeedGrepFilesName()

    def getGrepRule(self):
        return '%s'

    def getGrepKeys(self, unusedTargets):
        unusedKeys = []
        for target in unusedTargets:
            idx = target.rfind('/')
            if idx != -1:
                targetBaseName = target[(idx + 1):]
            else:
                targetBaseName = target

            idx = targetBaseName.find('.')
            if idx != -1:
                targetBaseName = targetBaseName[0:idx]

            keyArr = []
            keyArr.append(target)
            keyArr.append(targetBaseName)
            unusedKeys.append(keyArr)
        return unusedKeys

    def start(self):
        notFoundtags = []
        threads = []

        print ">>> begin <<<"
        printLock = multiprocessing.Lock()

        queue = multiprocessing.Queue()
        for i in self.unusedKeys:
            queue.put(i)

        for i in range(0, self.threadNum):
            outQueue = multiprocessing.Queue()
            notFoundtags.append(outQueue)
            t = multiprocessing.Process(target=grepThreadRun,
                                        args=(self.rule, self.ndGrepFName, outQueue,
                                              "%s T%s" % (self.getType(), i), queue, printLock, self.suffixGrepCmd,))
            t.start()
            threads.append(t)

        while queue.empty() is False:
            time.sleep(30)
        time.sleep(30)
        # threads[0].join()
        print ">>> thread %s end" % i

        for i in notFoundtags:
            while i.empty() is False:
                self.notFoundTags.append(i.get())
        os.remove(self.ndGrepFName)
        print ">>> end <<<"

    def getFilesBySuffix(self, suffixGrepCmd="", suffix="", prefix=""):
        if suffix != "":
            suffixRe = r"^%s.*\.%s$" % (prefix, suffix)
        else:
            suffixRe = r"^%s.*$" % prefix
        cmdStr = 'grep "%s" "%s" -w %s' % (suffixRe, self.listFileName, suffixGrepCmd)
        p = subprocess.Popen(cmdStr, stdout=subprocess.PIPE, shell=True)
        return p.stdout.read()

    def getNeedGrepFilesName(self, suffixGrepCmd="", suffix="", prefix=""):
        fileName = tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1]
        tmpFile = file(fileName, 'r+')
        tmpFile.write(self.getFilesBySuffix(suffixGrepCmd, suffix, prefix))
        tmpFile.close()
        return fileName

    def getUnusedTargetsList(self, suffixGrepCmd="", suffix="", prefix=""):
        savedTags = self.getSavedTags()
        if len(savedTags) > 0:
            grepCmd = savedTags[0]
            for i in range(1, len(savedTags)):
                grepCmd = "%s|%s" % (grepCmd, savedTags[i])
            suffixGrepCmd = '%s | egrep -v "%s"' % (suffixGrepCmd, grepCmd)
        return self.getFilesBySuffix(suffixGrepCmd, suffix, prefix).split('\n')

    def getSuffixGrepCmd(self):
        return ""

    def getType(self):
        return ""

    def getSavedTags(self):
        return SAVED_TAGS[self.getType()]

class libMultiGrep(multiGrep):
    def getGrepKeys(self, unusedTargets):
        unusedKeys = multiGrep.getGrepKeys(self, unusedTargets)
        for keyArr in unusedKeys:
            keyArr.append(re.sub(r'^lib', '', keyArr[1]))

        return unusedKeys

    def getUnusedTargetsList(self):
        return multiGrep.getUnusedTargetsList(self, '', 'so', '.*/lib/lib')

    def getNeedGrepFilesName(self):
        fileName = tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1]
        tmpFile = file(fileName, 'r+')
        tmpFile.write(multiGrep.getFilesBySuffix(self, r'| egrep -v ".*\.png|.*\.jpg|.*\.bmp"'))
        tmpFile.close()
        return fileName

    def getType(self):
        return "LIB"

class etcMultiGrep(multiGrep):
    def getUnusedTargetsList(self):
        return multiGrep.getUnusedTargetsList(self, '', '', '.*/etc/')

    def getType(self):
        return "ETC"

#    def getNeedGrepFilesName(self):
#        tmpFile = file(tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1], 'r+')
#        smaliList = multiGrep.getFile\sBySuffix(self, "smali")
#        xmlList = multiGrep.getFilesBySuffix(self, "xml")
#        tmpFile.write(smaliList)
#        tmpFile.write(xmlList)
#        return tmpFile


class drawableMultiGrep(multiGrep):
    def getGrepRule(self):
        return 'drawable.*%s'

    def getUnusedTargetsList(self):
        global frameworkApks
        pngList = []
        jpgList = []
        for frwApk in frameworkApks:
            pngList = multiGrep.getUnusedTargetsList(self, '', "png", frwApk) + pngList
            jpgList = multiGrep.getUnusedTargetsList(self, '', "jpg", frwApk) + jpgList
        return pngList + jpgList

    def getNeedGrepFilesName(self):
        smaliList = multiGrep.getFilesBySuffix(self, "| egrep -v \'/R\.smali|/R\$.*\.smali\'", "smali")
        xmlList = multiGrep.getFilesBySuffix(self, '| grep -v "public\.xml"', "xml")

        fileName = tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1]
        tmpFile = file(fileName, 'r+')
        tmpFile.write(smaliList)
        tmpFile.write(xmlList)
        tmpFile.close()
        return fileName

    def getType(self):
        return "DRAWABLE"

def getFilesInDir(inDir):
    p = subprocess.Popen("find %s -type f" % inDir, stdout=subprocess.PIPE, shell=True)
    return p.stdout.read()

def install_frameworks(frameworkDir):
    global HOME
    threads = []
    apkRe = re.compile(r'.*\.apk')
    if os.path.isdir("%s/apktool" % HOME):
        shutil.rmtree("%s/apktool" % HOME)

    for frwFile in os.listdir(frameworkDir):
        if bool(apkRe.match(frwFile)) is True:
            print ">>> apktool if %s/%s" % (frameworkDir, frwFile)
            threads.append(subprocess.Popen("%s if %s/%s" % (APKTOOL, frameworkDir, frwFile),
                                            stdout=subprocess.PIPE, shell=True))
    for t in threads:
        t.wait()

def turnIdToname(systemDir, frameworkApks):
    frameworkDir = "%s/framework" % systemDir
    isFrameworkRe = re.compile(r'isFrameworkApk: *true')
    publicXmlList = os.popen('find %s -type f -name "public.xml"' % (frameworkDir)).readlines()
    print ">>> start turning the res id to name, this might take several minutes, please wait ..."

    for publicXml in publicXmlList:
        publicXml = publicXml.replace('\n', '')
        apkDir = os.path.dirname(os.path.dirname(os.path.dirname(publicXml)))
        apktoolYml = "%s/apktool.yml" % apkDir
        apktoolYmlFd = file(apktoolYml, 'r')
        ymlStr = apktoolYmlFd.read()

        if isFrameworkRe.search(ymlStr):
            idtoname.idtoname(publicXml, systemDir).idtoname()
            frameworkApks.append(apkDir)
        apktoolYmlFd.close()

    print ">>> turn res id to name done <<<"

def prepare(inputArg, outDir, frameworkApks):
    print ">>> prepare files for grep"
    if (zipfile.is_zipfile(inputArg)):
        print ">>> extract %s to %s" % (inputArg, outDir)
        zFile = zipfile.ZipFile(inputArg, 'r')
        zFile.extractall(outDir)
    elif os.path.isdir(inputArg):
        print ">>> %s is an directory" % (inputArg)
        outDir = inputArg
        # subprocess.Popen('cp -rf %s/* %s' % (inputArg, outDir),
        #                 stdout=subprocess.PIPE, shell=True).wait()
    else:
        raise ">>> parameter %s is wrong" % inputArg

    if os.path.isdir("%s/SYSTEM" % outDir):
        subprocess.Popen('mv "%s/SYSTEM" "%s/system"' % (outDir, outDir),
                         stdout=subprocess.PIPE, shell=True).wait()

    systemDir = "%s/system" % outDir
    if os.path.exists(systemDir):
        install_frameworks("%s/framework" % systemDir)

        smaliDir = tempfile.mkdtemp()
        print ">>> begin decode apk and jar in %s to %s" % (systemDir, smaliDir)
        p = subprocess.Popen("%s %s %s" % (DECODE_ALL, systemDir, smaliDir),
                             stdout=subprocess.PIPE, shell=True)
        p.wait()
        time.sleep(10)
        # print p.stdout.read()

        threads = []
        subprocess.Popen('sync',
                         stdout=subprocess.PIPE, shell=True).wait()
        for sDir in os.listdir(smaliDir):
            if os.path.isdir("%s/%s" % (smaliDir, sDir)):
                threads.append(subprocess.Popen('mv %s/%s/* %s/%s' % (smaliDir, sDir, systemDir, sDir),
                                                stdout=subprocess.PIPE, shell=True))

        print ">>> begin delete apk and jar in %s" % systemDir
        p1 = subprocess.Popen('find %s -type f -name "*.apk" | xargs rm -rf' % (systemDir),
                              stdout=subprocess.PIPE, shell=True)
        p2 = subprocess.Popen('find %s -type f -name "*.jar" | xargs rm -rf' % (systemDir),
                              stdout=subprocess.PIPE, shell=True)

        for t in  threads:
            t.wait()
        subprocess.Popen('sync',
                              stdout=subprocess.PIPE, shell=True).wait()
        turnIdToname(systemDir, frameworkApks)

        p1.wait()
        p2.wait()
        print ">>> begin mv %s to %s" % (smaliDir, systemDir)

        for rmDir in REMOVE_DIRS:
            rmDir = "%s/%s" % (outDir, rmDir)
            if os.path.isdir(rmDir):
                print ">>> remove %s" % rmDir
                shutil.rmtree(rmDir)
        for i in range(0, len(frameworkApks)):
            frameworkApks[i] = frameworkApks[i].replace(smaliDir, '%s/' % systemDir).replace('//', '/')
        subprocess.Popen('sync',
                         stdout=subprocess.PIPE, shell=True).wait()


    else:
        raise ">>> ERROR: %s doesn't exist!" % systemDir

def main():
#    tmpFile = file('/tmp/jock', 'r+')
#    tmpFile.seek(0, 0)
#    tmpFile.truncate()
    global frameworkApks

    if len(sys.argv) >= 2:
        print ">>> begin ...."
        grepStart = datetime.datetime.now()
        outDir = tempfile.mkdtemp()
        fileName = tempfile.mkstemp(suffix='', prefix='tmp', dir=None, text=False)[1]
        try:
            inputArg = sys.argv[1]
            if os.path.isdir(inputArg):
                outDir = inputArg
            else:
                outDir = tempfile.mkdtemp()

            print ">>> pareparing ..."
            prepare(inputArg, outDir, frameworkApks)

            allFilesStr = getFilesInDir(outDir)
            allFilesFd = file(fileName, 'r+')
            allFilesFd.write(allFilesStr)
            allFilesFd.close()

            libsGrepStart = datetime.datetime.now()
            libsNotFoundTagsArr = []
            libMultiGrep(fileName, libsNotFoundTagsArr).start()
            libsGrepEnd = datetime.datetime.now()

            etcGrepStart = datetime.datetime.now()
            etcNotFoundTagsArr = []
            etcMultiGrep(fileName, etcNotFoundTagsArr).start()
            etcGrepEnd = datetime.datetime.now()

            drawableGrepStart = datetime.datetime.now()
            drawableNotFoundTagsArr = []
            drawableMultiGrep(fileName, drawableNotFoundTagsArr).start()
            drawableGrepEnd = datetime.datetime.now()

            outFile = file(OUT_FILE_NAME, 'w+')
            outFile.seek(0, 0)
            outFile.truncate()

            print ">>> begin generate the vendor.remove.mk"
            outFile.write("# This files was generate by script, \n#used to config which files or drawables should be remove")
            outFile.write('\n# configuration for vendor_remove_files\n')
            outFile.write('vendor_remove_files += \\\n')
            for tag in (libsNotFoundTagsArr
                        + etcNotFoundTagsArr):
                outFile.write("\t%s \\\n" % re.sub(".*system/", "", tag))

            outFile.write('\n# configuration for remove_drawables\n')
            outFile.write('remove_drawables += \\\n')
            for tag in drawableNotFoundTagsArr:
                outFile.write("\t%s \\\n" % re.sub(".*system/framework/", "", tag))
            outFile.write('\n')
            outFile.close()

            libProcessingTime = libsGrepEnd - libsGrepStart
            etcProcessingTime = etcGrepEnd - etcGrepStart
            drawableProcessingTime = drawableGrepEnd - drawableGrepStart

            print ">>> getUnsedFiles done, out: %s" % OUT_FILE_NAME
            print ">>> processing time on lib: %s" % libProcessingTime
            print ">>> processing time on etc: %s" % etcProcessingTime
            print ">>> processing time on drawable: %s" % drawableProcessingTime
            print ">>> total: %s" % (drawableGrepEnd - grepStart)
        finally:
            print "FINISHED!"
            if sys.argv[1] != outDir and os.path.isdir(outDir):
                os.popen("rm -rf %s" % outDir)
            if os.path.exists(fileName):
                os.popen("rm -rf %s" % fileName)

    else:
        print "Usage: getUnusedFiles.py ota.zip/target-files.zip"


if __name__ == '__main__':
    main()
