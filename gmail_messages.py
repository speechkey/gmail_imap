import email
import string
import re
from email.parser import HeaderParser
import gmail_message


class gmail_messages:
    def __init__(self, gmail_server):
        self.server = gmail_server
        self.mailbox = None
        self.messages_data = None
        self.messages = list()

    def parseFlags(self, flags):
        return flags.split()  # Note that we don't remove the '\' from flags, just split by space

    def parseMetadata(self, entry):
        if(not getattr(self, 'metadataExtracter', False)):
            self.metadataExtracter = re.compile(r'(?P<id>\d*) \(UID (?P<uid>\d*) FLAGS \((?P<flags>.*)\)\s')
            #  I hate regexps.
            #  (\d*) = MSG ID,  the position index of the message in its mailbox
            #  \(UID (\d*) = MSG UID, the unique id of this message within its mailbox
            #  FLAGS \((.*)\)\s = MSG FLAGS, special indicators like (\Starred, \Seen) may be empty
                    #example:  55 (UID 82 FLAGS (\Seen) BODY[HEADER.FIELDS (SUBJECT FROM)] {65}
                    #               groupdict() = { id:'55', uid:'82', flags:'\\Seen' }

        metadata = self.metadataExtracter.match(entry).groupdict()
        metadata['flags'] = self.parseFlags(metadata['flags'])
        return metadata

    def parseHeaders(self, entry):
        if(not getattr(self, 'headerParser', False)):
            self.headerParser = HeaderParser()

        headers = self.headerParser.parsestr(entry)
        return headers

    def search(self, mailbox, searchQuery):
        self.mailbox = mailbox

        if(not self.server.loggedIn):
            self.server.login()

        result, message = self.server.imap_server.select(mailbox, readonly=1)
        if result != 'OK':
            raise Exception(message)
        typ, self.messages_data = self.server.imap_server.search(None, searchQuery)
        return typ

    def process(self):
        self.messages = list()
        fetch_list = string.split(self.messages_data[0])[-10:]
        fetch_list = ','.join(fetch_list)

        if(fetch_list):
            f = self.server.imap_server.fetch(fetch_list, '(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
            for fm in f[1]:
                if(len(fm) > 1):
                    metadata = self.parseMetadata(fm[0])
                    headers = self.parseHeaders(fm[1])

                    message = gmail_message.gmail_message()
                    message.id = metadata['id']
                    message.uid = metadata['uid']
                    message.flags = metadata['flags']

                    message.date = headers['Date']
                    message.From = headers['From']
                    if('Subject' in headers):
                        message.Subject = headers['Subject']

                    self.messages.append(message)

    def __repr__(self):
        return "<gmail_messages:  \n%s\n>" % (self.messages)

    def __getitem__(self, key):
        return self.messages[key]

    def __setitem__(self, key, item):
        self.messages[key] = item

    def getMessage(self, uid):
        if(not self.server.loggedIn):
            self.server.login()
        self.server.imap_server.select(self.mailbox)

        status, data = self.server.imap_server.uid('fetch', uid, 'RFC822')
        messagePlainText = ''
        messageHTML = ''
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                for part in msg.walk():
                    message_type = part.get_content_type()
                    message_charset = part.get_content_charset()
                    if str(message_type) == 'text/plain':
                        messagePlainText = messagePlainText + str(part.get_payload())
                    if str(message_type) == 'text/html':
                        messageHTML = messageHTML + str(part.get_payload())

        #create new message object
        message = gmail_message.gmail_message()

        if(messageHTML != ''):
            message.Body = messageHTML
        else:
            message.Body = messagePlainText
        if('Subject' in msg):
            message.Subject = msg['Subject']
        message.From = msg['From']

        message.uid = uid
        message.mailbox = self.mailbox
        message.date = msg['Date']
        message.type = message_type
        message.charset = message_charset

        return message

    def deleteMessage(self, uid):
        if(not self.server.loggedIn):
            self.server.login()

        result = self.server.imap_server.uid('COPY', uid, '[Gmail]/Trash')

        if result[0] == 'OK':
            mov, data = self.server.imap_server.uid('STORE', uid, '+FLAGS', '(\Deleted)')
            self.server.imap_server.expunge()
