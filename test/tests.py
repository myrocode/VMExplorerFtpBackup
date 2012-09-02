from datetime import datetime
import VMExplorerFtpBackup
import unittest

class testVMExplorerFtpBackup(unittest.TestCase):
    def testMergeBackups(self):
        sourceBackUp = {
                        'Bart' :   {
                                        dateFromString('21/11/06 16:30') : [ 'bartFile1.txt','bartFile1.2.txt'],
                                        dateFromString('21/11/06 16:31') : [ 'bartFile2','file.txt2.2']
                                    },
                        'Raoul' :  {
                                        dateFromString('21/11/16 16:3') :  [ 'raoulFile1,txt']
                                    }
                        }
        destinationBackUp = {
                        'Miro' :   {
                                        dateFromString('21/11/46 16:30') : [ 'bartFile1.txt','bartFile1.2.txt'],
                                        dateFromString('21/11/45 16:30') : [ 'bartFile2','file.txt2.2']
                                    },
                        'Bart' :  {
                                        dateFromString('22/11/06 10:21') :  [ 'raoulFileMarge,txt']
                        }

        }

        result = VMExplorerFtpBackup.mergeBackup(sourceBackUp, destinationBackUp)

        # Bart checking
        self.assertTrue('Bart' in result)
        # first backup
        dateKey = dateFromString('21/11/06 16:30')
        self.assertTrue(dateKey in result['Bart'])
        listOfFiles = result['Bart'][dateKey]
        self.assertEqual(listOfFiles[0], 'bartFile1.txt')
        self.assertEqual(listOfFiles[1], 'bartFile1.2.txt')

        # second backup
        dateKey =dateFromString('21/11/06 16:31')
        self.assertTrue(dateKey in result['Bart'])
        listOfFiles = result['Bart'][dateKey]
        self.assertEqual(listOfFiles[0], 'bartFile2')
        self.assertEqual(listOfFiles[1], 'file.txt2.2')

        #third backup (the merged backup)
        dateKey =dateFromString('22/11/06 10:21')
        self.assertTrue(dateKey in result['Bart'])
        listOfFiles = result['Bart'][dateKey]
        self.assertEqual(listOfFiles[0], 'raoulFileMarge,txt')

        # other backups..
        self.assertTrue('Raoul' in result)
        self.assertTrue(dateFromString('21/11/16 16:30') in result['Raoul'])
        self.assertTrue('Miro' in result)
        self.assertTrue(dateFromString('21/11/46 16:30') in result['Miro'])
        self.assertTrue(dateFromString('21/11/45 16:30') in result['Miro'])

    def testSortAndRemoveOldBackups(self):
        backup= { 'Bart' :   {
            dateFromString('21/11/06 16:25') : [ 'bartFile1.txt','bartFile1.2.txt'],
            dateFromString('21/11/06 16:31') : [ 'bartFile2','file.txt2.2'],
            dateFromString('21/11/06 16:26') : [ 'bartFile2','file.txt2.2'],
            dateFromString('23/11/06 16:31') : [ 'bartFile2','file.txt2.2'],
            dateFromString('24/11/06 16:31') : [ 'bartFile2','file.txt2.2'],
            dateFromString('21/10/06 16:31') : [ 'bartFile2','file.txt2.2'],
            dateFromString('21/10/05 16:31') : [ 'bartFile2','file.txt2.2'],
            dateFromString('21/10/03 16:31') : [ 'bartFile2','file.txt2.2']
                 }
            }
        VMExplorerFtpBackup.sortAndRemoveOldBackups(backup, 5)
        bartBackup = backup['Bart']
        self.assertEquals(bartBackup.__len__(), 5)
        vmKeys = bartBackup.keys()
        self.assertEqual(vmKeys[0], dateFromString('21/10/04 16:31'))


def dateFromString(date):
    return datetime.strptime(date, "%d/%m/%y %H:%M")