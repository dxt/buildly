#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import lib as buildly
import subprocess
import time

def build(branchDirectory, configData, projectDirectory):
    target = configData['target']
    output = os.path.expanduser(configData['output_directory'])
    icon_directory = configData['configurations'].get('release', {}).get('icon_directory')
    replacementIconsDirectory = os.path.join(projectDirectory, icon_directory) if icon_directory else None
    ipaPackageHook = configData['configurations'].get('release', {}).get('ipa_package_hook')
    if ipaPackageHook: ipaPackageHook = os.path.join(projectDirectory, ipaPackageHook)
    mobileprovision = configData['configurations'].get('release', {}).get('mobileprovision')
    mobileprovision = os.path.join(projectDirectory, mobileprovision) if mobileprovision else None
    displayName = configData['configurations'].get('release', {}).get('display_name')
    identity = configData['configurations'].get('release', {}).get('identity')
    return buildly.buildPublish(branchDirectory, target, output, ipaPackageHook, displayName, mobileprovision, replacementIconsDirectory, identity)

def distribute(app, dsym, branchDirectory, config, configData, projectDirectory):
    target = configData['target']
    output = os.path.expanduser(configData['output_directory'])
    icon_directory = configData['configurations'][config].get('icon_directory')
    replacementIconsDirectory = os.path.join(projectDirectory, icon_directory) if icon_directory else None
    ipaPackageHook = configData['configurations'][config].get('ipa_package_hook')
    if ipaPackageHook: ipaPackageHook = os.path.join(projectDirectory, ipaPackageHook)
    mobileprovision = configData['configurations'][config].get('mobileprovision')
    mobileprovision = os.path.join(projectDirectory, mobileprovision) if mobileprovision else None
    display_name = configData['configurations'][config].get('display_name')
    identity = configData['configurations'][config].get('identity')
    hockeyArgs = configData['configurations'][config]['hockeyapp']
    hockeyArgs['notes'] = buildly.releaseNotes(branchDirectory, **hockeyArgs)

    if config == 'release':
        buildly.releaseBuild(app, dsym, branchDirectory, target, output, ipaPackageHook, **hockeyArgs)
    else:
        buildly.hockeyappUpload(app, dsym, display_name, replacementIconsDirectory,
            mobileprovision, identity, ipaPackageHook, **hockeyArgs)
    print '%(config)s build complete!' % locals()

def runConfig(config, configData, projectDirectory, branchesDirectory):
    target = configData['target']
    postBuildHook = configData['configurations'][config].get('post_build_hook')
    if postBuildHook: postBuildHook = os.path.join(projectDirectory, postBuildHook)
    branchName = configData['configurations'][config]['git_branch']
    branchDirectory = os.path.join(branchesDirectory, branchName)
    if not os.path.isdir(branchDirectory):
        buildly.git.clone(configData['git_repo'], branchDirectory, branchName)
    else:
        buildly.git.pull(branchDirectory)

    lastVersion = None
    version = buildly.projectVersion(branchDirectory, target)
    versionFilepath = os.path.join(branchesDirectory, branchName+'.version')
    if os.path.isfile(versionFilepath):
        with open(versionFilepath, 'r') as versionFile:
            lastVersion = versionFile.read().strip()

    if version == lastVersion:
        print 'Nothing new to build: %(config)s %(version)s from %(branchName)s' % locals()
        return

    print 'Buildling: %(config)s %(version)s from %(branchName)s' % locals()

    app, dsym = build(branchDirectory, configData, projectDirectory)
    distribute(app, dsym, branchDirectory, config, configData, projectDirectory)

    with open(versionFilepath, 'w') as versionFile:
        versionFile.write(version)

    buildly.git.tagBuild(branchDirectory, version)

    if config == 'release':
        buildly.git.tagRelease(branchDirectory, version)

    buildly.runScript(postBuildHook, buildly.projectShortVersion(branchDirectory, target))

def readConfig(configFile):
    print time.strftime("%c")
    if not configFile: raise RuntimeError('No config plist specified')
    if not os.path.isfile(configFile): raise RuntimeError('Config plist does not exist: %s' % configFile)

    projectDirectory = os.path.abspath(os.path.dirname(configFile))
    buildly.git.pull(projectDirectory)

    configData = buildly.plistlib27.readPlist(configFile)
    branchesDirectory = os.path.join(projectDirectory, 'branches')
    if not os.path.isdir(branchesDirectory):
        os.makedirs(branchesDirectory)

    for config in configData['configurations']:
        runConfig(config, configData, projectDirectory, branchesDirectory)

configFile = None
if len(sys.argv) > 0:
    configFile = os.path.abspath(sys.argv[1])

while(1):
    readConfig(configFile)
    time.sleep(10*60)
