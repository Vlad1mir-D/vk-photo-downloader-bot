import vk_api as vk
import vk_api.bot_longpoll as longpoll
from random import randint

from datetime import datetime

class vk_wrapper:
    
    def __init__(self, access_token, group_id, api_version = '5.103'):
        self.__group_id = group_id
        self.__vk_main = vk.VkApi(token = access_token, api_version = api_version)
        self.__server = longpoll.VkBotLongPoll(self.__vk_main, group_id)
        self.longpoll = longpoll
        self.__uploader = vk.upload.VkUpload(self.__vk_main)
        self.__event = None

    def listen(self):
        for event in self.__server.listen():
            self.__event = event.obj
            yield event

    @staticmethod
    def get_message_params(event, attachments = None):
        return {
            'user_id': event['peer_id'],
            'message': event['text'] if event['text']!='' else 'None',
            'random_id': randint(0, 99999999999999)
        }

    @staticmethod
    def get_full_message(event, vk_main):
        params = {
            'message_ids': event['id'],
            'preview_length': '0'
        }
        return vk_main.method('messages.getById', params)['items'][0]

    @staticmethod
    def get_message_attachments(message):
        result = message['attachments']
        for fwd_message in message.get('fwd_messages', []):
            result.extend(vk_wrapper.get_message_attachments(fwd_message))
        
        return result

    @staticmethod
    def filter_attachments(attachments, at_type):
        result = []
        for attachment in attachments:
            if (attachment['type'] in at_type):
                attachment[attachment['type']]['type'] = attachment['type']
                result.append(attachment[attachment['type']])
        
        return result

    @staticmethod
    def get_attachment(attachment):
        if attachment['type'] == 'photo':
            if attachment['orig_photo'] is not None and attachment['orig_photo']['url'] is not None:
                return {
                        'id': attachment['id'],
                        'owner_id': attachment['owner_id'],
                        'date': attachment['date'],
                        'url': attachment['orig_photo']['url'],
                        'type': attachment['type']
                     }

            sizes = ['s','m','x','o','p','q','r','y','z','w']
            best_size = max(attachment['sizes'], key = lambda size: sizes.index(size['type']))
            return {
                    'id': attachment['id'],
                    'owner_id': attachment['owner_id'],
                    'date': attachment['date'],
                    'url': best_size['url'],
                    'type': attachment['type']
                }

        elif attachment['type'] == 'doc':
            if attachment['url'] is not None:
                return {
                        'id': attachment['id'],
                        'owner_id': attachment['owner_id'],
                        'date': attachment['date'],
                        'url': attachment['url'],
                        'title': attachment['title'],
                        'ext': attachment['ext'],
                        'type': attachment['type']
                    }

            sizes = ['s','m','x','y','z','o']
            best_size = max(attachment['preview']['photo']['sizes'], key = lambda size: sizes.index(size['type']))
            return {
                    'id': attachment['id'],
                    'owner_id': attachment['owner_id'],
                    'date': attachment['date'],
                    'url': best_size['src'],
                    'title': attachment['title'],
                    'ext': attachment['ext'],
                    'type': attachment['type']
                }

        elif attachment['type'] == 'video':
             return {
                    'id': attachment['id'],
                    'owner_id': attachment['owner_id'],
                    'date': attachment['date'],
                    'title': attachment['title'] if 'title' in attachment else None,
                    'type': attachment['type']
                }

    def get_attachments(self):
        message = self.get_full_message(self.__event['message'], self.__vk_main)
        attachments = self.get_message_attachments(message)
        return [self.get_attachment(attachment) for attachment in self.filter_attachments(attachments, ['photo', 'doc', 'video'])]

    def get_command(self):
        return self.__event['message']['text']

    def get_message_id(self):
        return self.__event['message']['id']

    def get_peer_id(self):
        return self.__event['message']['peer_id']

    def get_from_id(self):
        return self.__event['message']['from_id']

    def get_id(self):
        return self.__event['message']['id']

    def get_date(self):
        return self.__event['message']['date']

    def send_message(self, message = '', attachments = None, reply_to = None):
        peer_id = self.get_peer_id()
        
        # try:
        #     if not attachment is None:  
        #         attachment = self.__uploader.document_message(attachment, peer_id = peer_id)
        # except:
        #     message += "\nError: can't upload attachment."
        #     attachment = None

        i = 0
        if not attachments is None and len(attachments) > 0:
            for attachment in attachments:
                i += 1
                attachment_title = '{}_{}_{:%Y-%m-%d_%H:%M:%S}_{}.zip'.format(
                        self.get_from_id(),
                        self.get_id(),
                        datetime.fromtimestamp(self.get_date()),
                        i
                    ) if len(attachments) > 1 else '{}_{}_{:%Y-%m-%d_%H:%M:%S}.zip'.format(
                        self.get_from_id(),
                        self.get_id(),
                        datetime.fromtimestamp(self.get_date()),
                    )
                attachment = self.__uploader.document_message(
                        attachment,
                        peer_id = peer_id,
                        title = attachment_title
                    )
                print('attachment', attachment)

                params = {
                    'user_id': peer_id,
                    'attachment': 'doc{owner_id}_{id}'.format(**attachment['doc']),
                    'message': message,
                    'random_id': randint(0, 99999999999),
                    'reply_to': reply_to
                }
                self.__vk_main.method('messages.send', params)

        else:
            params = {
                'user_id': peer_id,
                'message': message,
                'random_id': randint(0, 99999999999),
                'reply_to': reply_to
            }
            self.__vk_main.method('messages.send', params)


