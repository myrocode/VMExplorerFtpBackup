__author__ = 'myo'
import smtplib
__user = 'VMExplorerFtpBackup@dev4side.com'

#http://www.mkyong.com/python/how-do-send-email-in-python-via-smtplib/

def send_email_with_log(SmtpInfo, useSubjectWithError = False):
    smtpserver = smtplib.SMTP(SmtpInfo['smtpserver'])
    smtpserver.ehlo()
    if(useSubjectWithError):
        header = 'To:' + SmtpInfo['to'] + '\n' + 'From: ' + SmtpInfo['from'] + '\n' + 'Subject:'+ SmtpInfo['subjectWithError'] + '\n'
    else:
        header = 'To:' + SmtpInfo['to'] + '\n' + 'From: ' + SmtpInfo['from'] + '\n' + 'Subject:'+ SmtpInfo['subject'] + '\n'
    msg = header + '\n'+ readLogFile() + '\n\n'
    smtpserver.sendmail(SmtpInfo['from'],SmtpInfo['to'], msg)
    smtpserver.close()

def readLogFile():
    try:
        inputFile = open('VMExplorer.log', 'r')     #Open test.txt file in read mode
        textIntoFile = inputFile.read()
        inputFile.close()
        return textIntoFile
    except Exception:
        return "Cannot locate VMExplorer.log!"
