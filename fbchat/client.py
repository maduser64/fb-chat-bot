"""
    fbchat
    ~~~~~~

    Facebook Chat (Messenger) for Python

    :copyright: (c) 2015      by Taehoon Kim.
    :copyright: (c) 2015-2016 by PidgeyL.
    :license: BSD, see LICENSE for more details.
"""
import requests
import json
from uuid import uuid1
from random import random, choice
from datetime import datetime
from bs4 import BeautifulSoup as bs
from mimetypes import guess_type
from .utils import *
from .models import *
import io
import time
import os
import sys
# URLs
LoginURL      = "https://m.facebook.com/login.php?login_attempt=1"
SearchURL     = "https://www.facebook.com/ajax/typeahead/search.php"
SendURL       = "https://www.facebook.com/messaging/send/"
ThreadsURL    = "https://www.facebook.com/ajax/mercury/threadlist_info.php"
ThreadSyncURL = "https://www.facebook.com/ajax/mercury/thread_sync.php"
MessagesURL   = "https://www.facebook.com/ajax/mercury/thread_info.php"
ReadStatusURL = "https://www.facebook.com/ajax/mercury/change_read_status.php"
DeliveredURL  = "https://www.facebook.com/ajax/mercury/delivery_receipts.php"
MarkSeenURL   = "https://www.facebook.com/ajax/mercury/mark_seen.php"
BaseURL       = "https://www.facebook.com"
MobileURL     = "https://m.facebook.com/"
StickyURL     = "https://0-edge-chat.facebook.com/pull"
PingURL       = "https://0-channel-proxy-06-ash2.facebook.com/active_ping"
UploadURL     = "https://upload.facebook.com/ajax/mercury/upload.php"
UserInfoURL   = "https://www.facebook.com/chat/user_info/"


class Client(object):
    """A client for the Facebook Chat (Messenger).

    See http://github.com/carpedm20/fbchat for complete
    documentation for the API.

    """

    def __init__(self, email, password, thread_fbid = None, debug = True, user_agent = None, max_retries = 5):
        """A client for the Facebook Chat (Messenger).

        :param email: Facebook `email` or `id` or `phone number`
        :param password: Facebook account password
        :param thread_fbid: If set, group messages are sent to this group by default

            import fbchat
            chat = fbchat.Client(email, password)

        """

        if not (email and password):
            raise ValueError("Email and password are required")

        self.email = email
        self.password = password
        self.thread_fbid = thread_fbid

        self.debug = debug
        self._session = requests.session()
        self.req_counter = 1
        self.seq = "0"
        self.payloadDefault={}
        self.client = 'mercury'
        self.listening = False

        if not user_agent:
            user_agent = choice(USER_AGENTS)

        self._header = {
            'Content-Type' : 'application/x-www-form-urlencoded,charset=utf-8',
            'Referer' : BaseURL,
            'Origin' : BaseURL,
            'User-Agent' : user_agent,
            'Connection' : 'keep-alive',
        }

        self.log("Logging in...")

        for i in range(1,max_retries+1):
            if not self.login():
                self.log("Attempt #{} failed{}".format(i,{True:', retrying'}.get(i<5,'')))
                time.sleep(1)
                continue
            else:
                self.log("Login successful")
                self.on_login()
                break
        else:
            raise Exception("Login failed. Check ID/password")


    def log(self, msg):
        """ Writes log to file. Each day has separate file """
        try:
            os.mkdir("log")
        except:
            pass

        msg = str(msg)

        msg = time.strftime("[%H:%M:%S] ", time.localtime()) + msg

        today = time.strftime("%Y-%m-%d", time.localtime()) + ".log"
        with open("log/" + today, "a", encoding = "utf-8") as outfile:
            outfile.write(msg + "\n")

        print(msg)

    def listen(self, markAlive = True):
        self.listening = True
        sticky, pool = self._getSticky()

        if self.debug:
            self.log("Listening...")

        self.on_listening()

        while self.listening:
            try:
                if markAlive: self.ping(sticky)
                try:
                    content = self._pullMessage(sticky, pool)
                    if content: self._parseMessage(content)
                except requests.exceptions.RequestException as e:
                    continue
            except KeyboardInterrupt:
                break
            except requests.exceptions.Timeout:
                pass

    def _setttstamp(self):
        for i in self.fb_dtsg:
            self.ttstamp += str(ord(i))
        self.ttstamp += '2'

    def _generatePayload(self, query):
        """
        Adds the following defaults to the payload:
          __rev, __user, __a, ttstamp, fb_dtsg, __req
        """
        payload = self.payloadDefault.copy()
        if query:
            payload.update(query)
        payload['__req'] = str_base(self.req_counter, 36)
        payload['seq'] = self.seq
        self.req_counter += 1
        return payload

    def _get(self, url, query=None, timeout=30):
        payload=self._generatePayload(query)
        return self._session.get(url, headers=self._header, params=payload, timeout=timeout)

    def _post(self, url, query=None, timeout=30):
        payload=self._generatePayload(query)
        return self._session.post(url, headers=self._header, data=payload, timeout=timeout)

    def _cleanPost(self, url, query=None, timeout=30):
        self.req_counter += 1
        return self._session.post(url, headers=self._header, data=query, timeout=timeout)

    def _postFile(self, url, files=None, timeout=30):
        payload=self._generatePayload(None)
        return self._session.post(url, data=payload, timeout=timeout, files=files)


    def login(self):
        if not (self.email and self.password):
            raise Exception("id and password or config is needed")

        soup = bs(self._get(MobileURL).text, "lxml")
        data = dict((elem['name'], elem['value']) for elem in soup.findAll("input") if elem.has_attr('value') and elem.has_attr('name'))
        data['email'] = self.email
        data['pass'] = self.password
        data['login'] = 'Log In'

        r = self._cleanPost(LoginURL, data)

        if 'home' in r.url:
            self.client_id = hex(int(random()*2147483648))[2:]
            self.start_time = now()
            self.uid = self._session.cookies['c_user']
            self.user_channel = "p_" + self.uid
            self.ttstamp = ''

            r = self._get(BaseURL)
            soup = bs(r.text, "lxml")
            self.fb_dtsg = soup.find("input", {'name':'fb_dtsg'})['value']
            self._setttstamp()
            # Set default payload
            self.payloadDefault['__rev'] = int(r.text.split('"revision":',1)[1].split(",",1)[0])
            self.payloadDefault['__user'] = self.uid
            self.payloadDefault['__a'] = '1'
            self.payloadDefault['ttstamp'] = self.ttstamp
            self.payloadDefault['fb_dtsg'] = self.fb_dtsg

            self.form = {
                'channel' : self.user_channel,
                'partition' : '-2',
                'clientid' : self.client_id,
                'viewer_uid' : self.uid,
                'uid' : self.uid,
                'state' : 'active',
                'format' : 'json',
                'idle' : 0,
                'cap' : '8'
            }

            self.prev = now()
            self.tmp_prev = now()
            self.last_sync = now()

            return True
        else:
            return False

    def getUsers(self, name):
        """Find and get user by his/her name

        :param name: name of a person
        """

        payload = {
            'value' : name.lower(),
            'viewer' : self.uid,
            'rsp' : "search",
            'context' : "search",
            'path' : "/home.php",
            'request_id' : str(uuid1()),
        }

        r = self._get(SearchURL, payload)
        self.j = j = get_json(r.text)

        users = []
        for entry in j['payload']['entries']:
            if entry['type'] == 'user':
                users.append(User(entry))
        return users # have bug TypeError: __repr__ returned non-string (type bytes)

    def __send(self, recipient_id, message, like, image_id, is_group):
        """Send a message to a user or group chat

        :param message: a text that you want to send
        :param recipient_id: the user id or thread id that you want to send a message to
        :param like: size of the like sticker you want to send
        :param image_id: id for the image to send, gotten from the UploadURL
        :param is_group: determines if the recipient_id is for user or a group
        """

        messageAndOTID=generateOfflineThreadingID()
        timestamp = now()
        date = datetime.now()
        data = { 'client': self.client,
                 'action_type' : 'ma-type:user-generated-message',
                 'author' : 'fbid:' + self.uid,
                 'timestamp' : timestamp,
                 'timestamp_absolute' : 'Today',
                 'timestamp_relative' : str(date.hour) + ":" + str(date.minute).zfill(2),
                 'timestamp_time_passed' : '0',
                 'is_unread' : False,
                 'is_cleared' : False,
                 'is_forward' : False,
                 'is_filtered_content' : False,
                 'is_filtered_content_bh': False,
                 'is_filtered_content_account': False,
                 'is_filtered_content_quasar': False,
                 'is_filtered_content_invalid_app': False,
                 'is_spoof_warning' : False,
                 'source' : 'source:chat:web',
                 'source_tags[0]' : 'source:chat',
                 'body' : message,
                 'html_body' : False,
                 'ui_push_phase' : 'V3',
                 'status' : '0',
                 'offline_threading_id':messageAndOTID,
                 'message_id' : messageAndOTID,
                 'threading_id':generateMessageID(self.client_id),
                 'ephemeral_ttl_mode:': '0',
                 'manual_retry_cnt' : '0',
                 'signatureID' : getSignatureID(),
                 'has_attachment' : image_id != None,
                 'specific_to_list[0]' : 'fbid:' + str(recipient_id),
                 'specific_to_list[1]' : 'fbid:' + str(self.uid) }


        if is_group: data["thread_fbid"] = recipient_id
        else: data["other_user_fbid"] = recipient_id

        if image_id: data['image_ids[0]'] = image_id

        if like: data["sticker_id"] = like

        r = self._post(SendURL, data)

        if self.debug:
            if r.status_code != 200:
                self.log(r)
                self.log(data)

        return r.ok

    def send(self, message, user_fbid, like = None):
        """Send message to user
        Args:
            message: text that to send
            user_fbid: the user fbid that to send a message to
            like (optional): size of the like sticker you want to send
        """

        return self.__send(user_fbid,message, like, None, False)

    def sendLike(self, like, user_fbid):
        """Send like to a user

        :param message: text that you want to send
        :param user_fbid: the user fbid that to send a message to
        :param like (optional): size of the like sticker you want to send
        """
        return self.__send(user_fbid, "", like, None, False)

    def sendRemoteImage(self, image, user_fbid, message = "", like = None):
        """Send an image from a URL

        :param message: a text that you want to send
        :param recipient_id: the user id or thread id that you want to send a message to
        :param image: URL for an image to download and send
        :param is_group: determines if the recipient_id is for user or thread
        """
        mimetype = guess_type(image)[0]
        remote_image = requests.get(image).content
        image_id = self.uploadImage({'file': (image, remote_image, mimetype)})

        return self.__send(user_fbid, message, None, image_id, False)

    def sendLocalImage(self, image, user_fbid, message = ""):
        """Send an image from a file path

        :param recipient_id: user fbid or thread fbid that you want to send a message to
        :param image: path to a local image to send
        :param message: text that you want to send
        :param is_group: determines if the recipient_id is for user or thread
        """
        mimetype = guess_type(image)[0]
        image_id = self.uploadImage({'file': (image, open(image), mimetype)})

        return self.__send(user_fbid, message, None, image_id, False)
    
    def group_send(self, message, thread_fbid = None, like = None):
        """Send a message to a group chat with given thread id

        :param message: text that you want to send
        :param thread_fbid: thread fbid that you want to send the message to
        :param like: size of the like sticker you want to send
        :param image: id for the image to send, gotten from the UploadURL
        """
        if not thread_fbid: 
            if not self.thread_fbid: raise ValueError("thread_id not given")
            thread_fbid = self.thread_fbid

        return self.__send(thread_fbid, message, like, None, True)

    def group_sendLike(self, like, thread_fbid = None):
        if not thread_fbid: 
            if not self.thread_fbid: raise ValueError("thread_id not given")
            thread_fbid = self.thread_fbid

        return self.__send(thread_fbid, "", like, None, True)


    def group_sendRemoteImage(self, image, thread_fbid = None, message = "", like = None):
        """Send an image from a URL

        :param message: text that you want to send
        :param thread_fbid: thread fbid that you want to send the message to
        :param image: URL for the image to download and send
        """
        if not thread_fbid: 
            if not self.thread_fbid: raise ValueError("thread_id not given")
            thread_fbid = self.thread_fbid

        return self.sendRemoteImage(thread_fbid, message, like, image, True)

    def group_sendLocalImage(self, image, thread_fbid = None, message = "", like = None):
        """Send an image from a file path

        :param message: text that you want to send
        :param thread_fbid: thread fbid that you want to send the message to
        :param image: path to the local image to send
        """
        if not thread_fbid: 
            if not self.thread_fbid: raise ValueError("thread_id not given")
            thread_fbid = self.thread_fbid

        return self.sendLocalImage(thread_fbid, message, like, image, True)

    def uploadImage(self, image):
        """Upload the image and get the image_id for sending in a message
        Args:
            image: tuple of (file name, data, mime type) to upload to facebook
        """
        r = self._postFile(UploadURL, image)
        if isinstance(r._content, str) is False:
            r._content = r._content.decode("utf-8")
        # Strip the start and parse out the returned image_id
        return json.loads(r._content[9:])['payload']['metadata'][0]['image_id']

    def getThreadInfo(self, userID, start, end = None):
        """Get the info of one Thread

        :param userID: ID of the user you want the messages from
        :param start: the start index of a thread
        :param end: (optional) the last index of a thread
        """

        if not end: end = start + 20
        if end <= start: end = start + end

        data = {}
        data['messages[user_ids][%s][offset]'%userID] =    start
        data['messages[user_ids][%s][limit]'%userID] =     end
        data['messages[user_ids][%s][timestamp]'%userID] = now()

        r = self._post(MessagesURL, query=data)
        if not r.ok or len(r.text) == 0:
            return None

        j = get_json(r.text)
        if not j['payload']:
            return None


        messages = []
        for message in j['payload']['actions']:
            messages.append(Message(**message))
        return list(reversed(messages))


    def getThreadList(self, start, end=None, thread_type='inbox'):
        """Get thread list of your facebook account.

        :param start: the start index of a thread
        :param end: (optional) the last index of a thread
        :param thread_type: (optional) "inbox", "pending", "archived"
        """

        if not end: end = start + 20
        if end <= start: end = start + end

        if thread_type in ['inbox', 'pending', 'archived']:
            if thread_type == 'archived':
                thread_type = 'action:archived'
        else:
            raise ValueError('thread_type must be "inbox", "pending" or "archived"')


        timestamp = now()
        date = datetime.now()
        data = {
            'client' : self.client,
            thread_type + '[offset]' : start,
            thread_type + '[limit]' : end,
        }

        r = self._post(ThreadsURL, data)
        if not r.ok or len(r.text) == 0:
            return None

        j = get_json(r.text)

        # Get names for people
        participants = {}
        try:
            if 'participants' in j['payload']:
                for participant in j['payload']['participants']:
                    participants[participant["fbid"]] = participant["name"]
        except Exception as e:
            self.log(j)

        threads = []
        # only get threads if any in this thread_type
        if 'threads' in j['payload']:
            # Prevent duplicates in self.threads
            threadIDs = [getattr(x, "thread_id") for x in threads]
            for thread in j['payload']['threads']:
                if thread["thread_id"] not in threadIDs:
                    try:
                        thread["other_user_name"] = participants[thread["other_user_fbid"]]
                    except:
                        thread["other_user_name"] = ""
                    t = Thread(**thread)
                    threads.append(t)

        return threads


    def getUnread(self):
        form = {
            'client': 'mercury_sync',
            'folders[0]': 'inbox',
            'last_action_timestamp': now() - 60*1000
            #'last_action_timestamp': 0
        }

        r = self._post(ThreadSyncURL, form)
        if not r.ok or len(r.text) == 0:
            return None

        j = get_json(r.text)
        result = {
            "message_counts": j['payload']['message_counts'],
            "unseen_threads": j['payload']['unseen_thread_ids']
        }
        return result

    def markAsDelivered(self, userID, threadID):
        data = {"message_ids[0]": threadID}
        data["thread_ids[%s][0]"%userID] = threadID
        r = self._post(DeliveredURL, data)
        return r.ok

    def markAsRead(self, userID):
        data = { "watermarkTimestamp": now(),
                 "shouldSendReadReceipt": True }
        data["ids[%s]"%userID] = True
        r = self._post(ReadStatusURL, data)
        return r.ok


    def markAsSeen(self):
        r = self._post(MarkSeenURL, {"seen_timestamp": 0})
        return r.ok


    def ping(self, sticky):
        data = {
            'channel': self.user_channel,
            'clientid': self.client_id,
            'partition': -2,
            'cap': 0,
            'uid': self.uid,
            'sticky': sticky,
            'viewer_uid': self.uid
        }
        r = self._get(PingURL, data)
        return r.ok


    def _getSticky(self):
        """
        Call pull api to get sticky and pool parameter,
        newer api needs these parameter to work.
        """

        data = {
            "msgs_recv": 0,
            "channel": self.user_channel,
            "clientid": self.client_id
        }

        r = self._get(StickyURL, data)
        j = get_json(r.text)

        if 'lb_info' not in j:
            raise Exception('Get sticky pool error')

        sticky = j['lb_info']['sticky']
        pool = j['lb_info']['pool']
        return sticky, pool


    def _pullMessage(self, sticky, pool):
        """
        Call pull api with seq value to get message data.
        """

        data = {
            "msgs_recv": 0,
            "sticky_token": sticky,
            "sticky_pool": pool,
            "clientid": self.client_id,
        }

        r = self._get(StickyURL, data)
        j = get_json(r.content.decode("utf-8"))

        self.seq = j.get('seq', '0')
        return j


    def _parseMessage(self, content):
        """
        Get message and author name from content.
        May contains multiple messages in the content.
        """

        if 'ms' not in content: return
        for msg in content['ms']:
            try:
                # Main things happen in here
                if msg['type'] in ['delta']:
                    delta = msg['delta']

                    if delta['class'] in ['ForcedFetch', 'MarkUnread']: return

                    if 'messageMetadata' in delta:
                        author_id = delta['messageMetadata']['actorFbId']
                        message_id = delta['messageMetadata']['messageId']
                        thread_fbid = delta['messageMetadata']['threadKey'].get('threadFbId', None)
                    else:
                        thread_key = delta.get('threadKey', None)
                        if not thread_key: delta.get('threadKeys', None)

                        if thread_key:
                            if 'otherUserFbId' in thread_key:
                                author_id = thread_key['otherUserFbId']
                                thread_fbid = None
                            author_id = delta['actorFbId']
                            thread_fbid = thread_key.get('threadFbId', None)
                        else: return # whatever I have more stuff to do than getting author_id

                    # New message received
                    if delta['class'] == 'NewMessage':
                        message = delta.get('body', '')
                        attachments = delta.get('attachments', '')
                        
                        if thread_fbid:
                            self.on_group_message(thread_fbid, author_id, message, attachments, message_id, delta)
                        else:
                            self.on_message(author_id, message, attachments, message_id, delta)

                    # Seen
                    elif delta['class'] == 'ReadReceipt':
                        seen_time = delta['actionTimestampMs']

                        if thread_fbid:
                            self.on_group_seen(thread_fbid, author_id, seen_time, delta)
                        else:
                            self.on_seen(author_id, seen_time, delta)

                    # Added to group
                    elif delta['class'] == 'ParticipantsAddedToGroupThread':
                        added_list = delta['addedParticipants']
                        self.on_group_added(thread_fbid, author_id, added_list, delta)

                    # Left the group
                    elif delta['class'] == 'ParticipantLeftGroupThread':
                        leaver_fbid = delta['leftParticipantFbId']
                        self.on_group_left(thread_fbid, author_id, leaver_fbid, delta)

                    # Changed title
                    elif delta['class'] == 'ThreadName':
                        new_title = delta['name']
                        self.on_group_titleChanged(thread_fbid, author_id, new_title, delta)

                    # Changed emoji
                    elif delta['type'] == 'change_thread_icon':
                        new_emoji = delta['untypedData']['thread_icon']
                            
                        if thread_fbid:
                            self.on_group_emojiChanged(thread_fbid, author_id, new_emoji, delta)
                        else:
                            self.on_emojiChanged(author_id, new_emoji, delta)

                    # Changed chat color
                    elif delta['type'] == 'change_thread_theme':
                        new_color = delta['untypedData']['theme_color']
                            
                        if thread_fbid:
                            self.on_group_colorChanged(thread_fbid, author_id, new_color, delta)
                        else:
                            self.on_colorChanged(author_id, new_color, delta)

                    # Changed nickname
                    elif delta['type'] == 'change_thread_nickname':
                        changed_fbid = delta['untypedData']['participant_id']
                        new_nickname = delta['untypedData']['nickname']
                            
                        if thread_fbid:
                            self.on_group_nicknameChanged(thread_fbid, author_id, changed_fbid, new_nickname, delta)
                        else:
                            self.on_nicknameChanged(author_id, changed_fbid, new_nickname, delta)

                    # Message delivered
                    elif delta['class'] == 'DeliveryReceipt':
                        time_delivered = delta['deliveredWatermarkTimestampMs']
                            
                        if thread_fbid:
                            self.on_group_messageDelivered(thread_fbid, author_id, time_delivered, delta)
                        else:
                            self.on_messageDelivered(author_id, time_delivered, delta)


                # Private message typing
                elif msg['type'] in ['typ']:
                    author_id = msg["from"]

                    if msg["st"] == 1:
                        self.on_typing(author_id, msg)
                    if msg["st"] == 0:
                        self.on_typing_stopped(author_id, msg)

                # Group chat typing
                elif msg['type'] == "ttyp":
                    thread_fbid = msg["thread"]
                    author_id = msg["from"]
                    
                    if msg["st"] == 1:
                        self.on_group_typing(thread_fbid, author_id, msg)
                    if msg["st"] == 0:
                        self.on_group_typing_stopped(thread_fbid, author_id, msg)


                elif msg['type'] in ['m_read_receipt']:
                    self.on_seen(msg.get('realtime_viewer_fbid'), msg.get('reader'), msg.get('time'))

                elif msg['type'] in ['inbox']:
                    viewer = msg.get('realtime_viewer_fbid')
                    unseen = msg.get('unseen')
                    unread = msg.get('unread')
                    other_unseen = msg.get('other_unseen')
                    other_unread = msg.get('other_unread')
                    timestamp = msg.get('seen_timestamp')
                    self.on_inbox(viewer, unseen, unread, other_unseen, other_unread, timestamp)

                # Have no idea what is this
                elif msg['type'] in ['qprimer', 'deltaflow']:
                    return

                # Probably never used anymore?
                elif msg['type'] in ['m_messaging', 'messaging']:
                    if msg['event'] in ['deliver']:
                        mid =     msg['message']['mid']
                        message = msg['message']['body']
                        author_id =    msg['message']['sender_fbid']
                        name =    msg['message']['sender_name']
                        #self.on_message(mid, author_id, message, msg)
                else:
                    if self.debug:
                        self.log(msg)
            except Exception as e:
                # ex_type, ex, tb = sys.exc_info()
                self.on_message_error(sys.exc_info(), msg)


    def getUserInfo(self, user_ids):
        """Get user info from id. Unordered.

        :param user_ids: one or more user id(s) to query
        """

        data = { "ids[{}]".format(i):user_id for i, user_id in enumerate(user_ids) }
        r = self._post(UserInfoURL, data)
        info = get_json(r.content.decode("utf-8"))
        full_data = [details for profile, details in info['payload']['profiles'].items()]
        if len(full_data) == 1:
            full_data = full_data[0]
        return full_data


    
    def on_login(self):
        pass

    def on_listening(self):
        pass


    def on_group_message(self, thread_fbid, author_id, message, attachements, mid, metadata):
        self.markAsDelivered(author_id, mid)
        self.markAsRead(author_id)

    def on_message(self, author_id, message, attachements, mid, metadata):
        self.markAsDelivered(author_id, mid)
        self.markAsRead(author_id)
        
        
    def on_group_typing(self, thread_fbid, author_id, metadata):
        self.log("%s typing in %s" % (author_id, thread_fbid))
        pass

    def on_typing(self, author_id, metadata):
        self.log("%s typing" % (author_id))
        pass


    def on_group_typing_stopped(self, thread_fbid, author_id, metadata):
        self.log("%s stopped typing in %s" % (author_id, thread_fbid))
        pass

    def on_typing_stopped(self, author_id, metadata):
        self.log("%s stopped typing" % (author_id))
        pass


    def on_group_seen(self, thread_fbid, author_id, time_seen, metadata):
        self.log("%s seen in %s at %s" % (author_id, thread_fbid, time_seen))
        pass

    def on_seen(self, author_id, time_seen, metadata):
        self.log("%s seen in at %s" % (author_id, time_seen))
        pass

    def on_group_nicknameChanged(self, thread_fbid, author_id, changed_fbid, new_nickname, delta):
        self.log("%s changed nickname of %s to %s in %s" % (author_id, changed_fbid, new_nickname, thread_fbid))
        pass

    def on_nicknameChanged(self, author_id, changed_fbid, new_nickname, delta):
        self.log("%s changed nickname of %s to %s" % (author_id, changed_fbid, new_nickname))
        pass
    

    def on_group_emojiChanged(self, thread_fbid, author_id, new_emoji, delta):
        self.log("%s changed emoji of %s to %s" % (author_id, thread_fbid, new_emoji))
        pass

    def on_emojiChanged(self, author_id, new_emoji, delta):
        self.log("%s changed emoji to %s" % (author_id, new_emoji))
        pass


    def on_group_colorChanged(self, thread_fbid, author_id, new_color, delta):
        self.log("%s changed color of %s to %s" % (author_id, thread_fbid, new_color))
        pass

    def on_colorChanged(self, author_id, new_color, delta):
        self.log("%s changed color to %s" % (author_id, new_color))
        pass
    

    def on_group_messageDelivered(self, thread_fbid, author_id, time_delivered, delta):
        self.log("Message delivered to %s in %s at %s" % (author_id, thread_fbid, time_delivered))
        pass

    def on_messageDelivered(self, author_id, time_delivered, delta):
        self.log("Message delivered to %s at %s" % (author_id, time_delivered))
        pass


    def on_group_added(self, thread_fbid, author_id, added_list, metadata):
        self.log("%s added %s people to %s" % (author_id, str(len(added_list)), thread_fbid))
        pass

    def on_group_left(self, thread_fbid, author_id, leaver_fbid, metadata):
        self.log("%s removed %s from %s" % (author_id, leaver_fbid, thread_fbid))
        pass

    def on_group_titleChanged(self, thread_fbid, author_id, new_title, delta):
        self.log("%s changed title of %s to %s" % (author_id, thread_fbid, new_title))
        pass


    def on_inbox(self, viewer, unseen, unread, other_unseen, other_unread, timestamp):
        """
        subclass Client and override this method to add custom behavior on event
        """
        pass

    def on_message_error(self, exception, message):
        """
        subclass Client and override this method to add custom behavior on event
        """
        self.log("Exception: " + str(exception))
