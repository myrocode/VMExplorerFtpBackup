'''
    VMExplorerFtpBackup is a simple program written in python 2.6 which
    aims to provide ftp support for the commercial program called VMExplorer.
    The purpose of the program is to upload your Virtual Machine's  backups
    to ftp servers and keeps track of the backup rotation.

    Copyright (C) 2012  Miro Radenovic

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import optparse
import logging

import backupManager
import backupRender
import backupSerializer
import ftpHostFactory
from subprocess import Popen

config = None

# program start

def main(params):

    _configure_logger(params.verbosity)
    _import_ftp_config(params.configFtp)


    try:
        if(params.rebuildDumpFile):
            answer = raw_input('This option will delete the current dump file and rebuild a new one. all backup statuses'' will be lost. press [Y] to confirm and continue\n')
            if answer.lower() == 'y':
                try:
                    logging.info('user selected option [Y] = delete old dump file and rebuild new one')
                    _rebuild_dump_file_from_backups_on_ftphosts(params.dumpFilePath)
                    logging.info('a new backup dump file has been created with the following backup info: \n{0}'.format(display_dump_file(params.dumpFilePath)))
                except Exception as ex:
                    logging.error(ex)
            else :
                print('ok, leaving... bye bye!')
        elif(params.status):
            display_dump_file(params.dumpFilePath)
        elif(params.start):
            start_backup(params.folder, params.dumpFilePath, params.numberOfBackups)

        # if everthing runs ok, then we can execute esternal programs if -x params has been specified.
        if params.execute != None:
            logging.debug('-x has been specified. running: {0}'.format(params.execute))
            p = Popen(params.execute)
            stdout, stderr = p.communicate()
            logging.debug(stdout)

    except Exception as ex:
        logging.error(ex)
        return 1

    logging.debug("the program has terminated. byee!")
    return 0

# programs options

def start_backup(vmFolderTreePath, vmBackupHistoryDumpFilePath, numberOfBackupsToKeep):
    '''
    starts the backup programs.
    Args:   vmFolderTreePath: str -> path of the folder that contains the virtual machines backups
            vmBackupHistoryDumpFilePath: str -> path to the dump file that stores the backupHistory
            numberOfBackupsToKeep: int -> number of tha max backups to keep. old backups will be removed
    '''
    backupsToUpload= backupManager.getBackupsFromFolderTree(vmFolderTreePath)
    logging.debug("folder tree inspection from path {0} has found the following backups that will be uploaded \n {1}".format(vmFolderTreePath, backupRender.get_backups_infos(backupsToUpload)))
    backupsInDumpFile = backupSerializer.get_backups_from_dump_file_or_None(vmBackupHistoryDumpFilePath)
    logging.debug("current backup status is (from dumpfile {0}) \n: {1}".format(vmBackupHistoryDumpFilePath, backupRender.get_backups_infos(backupsInDumpFile)))
    backups = get_merge_of_backups(backupsToUpload, backupsInDumpFile)
    logging.debug("the merging of the 2 backups is:\n {0}".format(backupRender.get_backups_infos(backups)))
    sort_and_remove_old_backups(backups, numberOfBackupsToKeep)
    logging.debug("cleaned old backups (max {0} backups), the result is;\n {1}".format(numberOfBackupsToKeep, backupRender.get_backups_infos(backups)))
    try:
        _upload_backups_to_ftp_server(vmFolderTreePath, backups)
    except Exception as ex:
        logging.error("An error occured while syncing the backup: {0}".format(ex))
        raise ex

    logging.debug("saving Virtual Machines uploads to the the dumpfile on path: {0}".format(vmBackupHistoryDumpFilePath))
    backupSerializer.saveBackupToDumpFile(backups, vmBackupHistoryDumpFilePath)
    logging.debug("the backups stored in the dump file are {0}".format(backupRender.get_backups_infos(backups)))


def _rebuild_dump_file_from_backups_on_ftphosts(dumpFilePath):
    '''
    rebuilds a new dump file by scanning all ftp server's defined in the configuration config.py file.
    Args: dumpFilePath: str -> the path of the dumpfile
    '''
    backups = {}
    for vmName in config.VmToFtp:
        if not vmName == '*':
            host = _get_ftpHost_by_vmName(vmName)
            backupsInFtpHost = backupManager.getBackupsFromFtpServer(host)
            _merge_first_backup_into_second_backup(backupsInFtpHost, backups)
    backupRender.get_backups_infos(backups)
    backupSerializer.saveBackupToDumpFile(backups, dumpFilePath)
    return backups


def display_dump_file(dumpFilePath):
    '''
    displays the content of the given dump file into the console
    Args: dumpFilePath: str -> the path of the dump file to display
    '''
    backupsToDisplay = backupSerializer.get_backups_from_dump_file_or_None(dumpFilePath)
    print(backupRender.get_backups_infos(backupsToDisplay))

#---------------------------
#   public helpers methods
#---------------------------


def get_merge_of_backups(backup1, backup2):
    '''
    merges 2 dictionary of backups into 1
    Args:   backup1 : dic -> first backup to merge
            backup2 : dic -> second backup to merge
    result: the dictionary of backups that stores all elements from  the backup1 and backup2.
    '''
    result ={}
    _merge_first_backup_into_second_backup(backup1, result)
    _merge_first_backup_into_second_backup(backup2, result)
    return result

def sort_and_remove_old_backups(backups, maxNumberOfBackupsToKeepForSingleVm):
    '''
    sorts given backup keeps only the first maxNumberOfBackupsToKeepForSingleVm backups
    '''
    for vmName in backups:
        vmBackups = backups[vmName]
        sortedBackup= get_only_new_backups(vmBackups, maxNumberOfBackupsToKeepForSingleVm)
        backups[vmName] = sortedBackup

def get_only_new_backups(dictionaryOfBackups, numberOfBackupsToTake):
    '''
    returns only the newest backups between specified range [0:numberOfBackupsToTake]
    Args:   dictionaryOfBackups: dic -> the dictionary of backups
            numberOfBackupsToTake : int -> number of backups to keep
            return: a new dictionary of backups that stores only latest backups
    '''
    result = {}
    keys = dictionaryOfBackups.keys()
    keys.sort()
    keys.reverse()
    keys = keys[0:int(numberOfBackupsToTake)]
    for key in keys:
        result[key] = dictionaryOfBackups[key]
    return result




#---------------------------
#     private methods
#---------------------------


def _upload_backups_to_ftp_server(vmPathBackupFolderTree, backups):
    '''
    uploads backups to the ftp server defined in the config file
    args:   vmPathBackupFolderTree: str -> the base folder tree path where the backups are stored in the local filesystem
            backups: dic -> a dictionary that holds the backups that needs to be uploaded to the server
    '''
    logging.info("Ftp sync will now start")
    for vmName in backups:
        ftphost = _get_ftpHost_by_vmName(vmName)
        logging.info("- backup's sync for virtual machine {0} with ftp server {1} begins:".format(vmName, ftphost.hostname))
        backupsToDelete, backupsToUpload = backupManager.get_backups_for_upload_and_delete(backups, ftphost)
        if len(backupsToDelete) > 0:
            backupManager.delete_backups_from_ftpHost(backupsToDelete, ftphost)
        if len(backupsToUpload) > 0:
            backupManager.upload_backups_to_ftpHost(backupsToUpload, ftphost, vmName, vmPathBackupFolderTree)

    logging.info("syncing to ftp has finished successfully")


def _merge_first_backup_into_second_backup(backupToJoin, destinationBackupToJoin):
    '''
    Merges 2 backups into 1
    Args: backupToJoin [dic] the source
     destinationBackupToJoin [dic] the result of the merge
    '''
    for vm in backupToJoin:
        if vm in destinationBackupToJoin:
            currentDestinationMachine = destinationBackupToJoin[vm]
            for dateOfBackup in backupToJoin[vm]:
                if not currentDestinationMachine.has_key(dateOfBackup):
                    currentDestinationMachine[dateOfBackup] = backupToJoin[vm][dateOfBackup]
        else : destinationBackupToJoin[vm] = backupToJoin[vm]

def _get_ftpHost_by_vmName(vmName):
    '''
    by a given vmName, return associated ftpHost. mappings are located in the config.py file
    Arg: vmName: str -> the virtual machine name.
    '''
    if config.VmToFtp.has_key(vmName):
        connectionInfo = config.VmToFtp[vmName]
    else:
        connectionInfo = config.VmToFtp['*']
        # connect to ftp server
    ftphost = ftpHostFactory.create_ftpHost(hostname=connectionInfo[0], port=connectionInfo[1], user=connectionInfo[2],password=connectionInfo[3], remoteFolder=connectionInfo[4])
    return ftphost

def _configure_logger(verbosity):
    '''
    configures the logger accordingly to the verbosity level
    arg: verbosity: str -> can be: info, warn, error, debug
    '''
    verbosityLevels =  {
        'info': logging.INFO,
        'warn': logging.WARNING,
        'error': logging.ERROR,
        'debug': logging.DEBUG,
        }
    try:
        logging.basicConfig(level=verbosityLevels[verbosity], format='%(message)s')
    except KeyError:
        print("an unknown verbosity option has been selected: {0}. the debug option will be selected automatically".format(verbosity))
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def _import_ftp_config(configToImport):
    try:
        global config
        config = __import__(configToImport, globals(), locals(), [], -1)
        logging.debug("the following machines have a defined ftp connection in the config file")
        for machineName in config.VmToFtp:
            logging.debug(machineName)
    except ImportError:
        logging.error("Cannot import configuration {0}. ".format(configToImport))


#---------------------------
#    program start
#---------------------------

if __name__ == "__main__":
    parser = optparse.OptionParser()
    # todo: how to use confilcs?
    # starts the backup and options
    parser.add_option('-s', '--start', help='starts the backup', dest='start', action="store_true", default=True)
    parser.add_option('-f', '--folder', help='sets the start folder to parse', dest='folder' ,default='.')
    parser.add_option('-d', '--dumpFilePath', help='path to dumpfile', dest='dumpFilePath' ,default='dump.dm')
    parser.add_option('-n', '--numberOfBackups', help='path to dumpfile', dest='numberOfBackups' ,default='3')
    parser.add_option('-c', '--configFtp', help='set the alternative config file that stores ftp connections', dest='configFtp', default='config')
    # rebuild the local database dump file
    parser.add_option('-r', '--rebuildDumpFile', help='recreates a new database dump file by reading backups stored into defined ftp sites', dest='rebuildDumpFile',  action="store_true", default=False)
    #display info options
    parser.add_option('-z', '--status', help='displays the status of the backups: info related to the next upload and the current dump file', dest='status', action="store_true", default=False)
    parser.add_option('-v', '--verbose', help='set the verbosity level. accepted values are: info, warn, error and debug', dest='verbosity', default='info')
    parser.add_option('-x', '--execute', help='runs a program if no errors occurs after the backup sync has performed', dest='execute')

    (opts, args) = parser.parse_args()
    main(opts)


