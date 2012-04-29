import imaplib
import sys
import os
from smtplib import SMTP
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
import gmail_mailboxes
import gmail_messages


class gmail_imap:
    def __init__(self, username, password):
        self.imap_server = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        self.username = username
        self.password = password
        self.loggedIn = False

        self.mailboxes = gmail_mailboxes.gmail_mailboxes(self)
        self.messages = gmail_messages.gmail_messages(self)

    def login(self):
        self.imap_server.login(self.username, self.password)
        self.loggedIn = True

    def logout(self):
        self.imap_server.close()
        self.imap_server.logout()
        self.loggedIn = False

    def sendmail(self, destination, subject, message, attach=None):
        try:
            msg = MIMEMultipart()

            msg['From'] = self.username
            msg['Reply-to'] = self.username
            msg['To'] = destination
            msg['Subject'] = subject

            msg.attach(MIMEText(message))

            if attach:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(open(attach, 'rb').read())
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(attach))
                msg.attach(part)

            mailServer = SMTP("smtp.gmail.com", 587)
            mailServer.ehlo()
            mailServer.starttls()
            mailServer.ehlo()
            try:
                mailServer.login(self.username, self.password)
                mailServer.sendmail(self.username, destination, msg.as_string())
            finally:
                mailServer.close()
        except Exception, exc:
            sys.exit("Failed to send mail; %s" % str(exc))

if __name__ == '__main__':
    gmail = gmail_imap('example@gmail.com', 'password')
    gmail.messages.search("INBOX", "(FROM info@facebook.com) (ALL SUBJECT friend)")
    gmail.messages.process()

    for msg in gmail.messages[0:10]:
        message = gmail.messages.getMessage(msg.uid)
        print message.date
        if message.type == 'text/html':
            print "text/html"
            print message.Body
        else:
            print "text/plain"
            print message.Body

    gmail.logout()
