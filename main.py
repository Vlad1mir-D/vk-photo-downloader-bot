from vk import vk_wrapper
import json
import os
from uuid import uuid1 as generate_id
import requests
from PIL import Image
import zipfile
from multiprocessing import Pool
import shutil

from datetime import datetime
from time import sleep
import yt_dlp

vkHandler = None

def init():
    global vkHandler

    if not os.path.isdir('userData'):
        os.mkdir("userData")

    config = {
        'access_token': None,
        'group_id': None,
        'api_version': '5.103'
    }

    if os.path.isfile('config.json'):
        with open('config.json') as config_file:
            config = json.load(config_file)
    else:
        with open('config.json', 'w') as config_file:
            json.dump(config, config_file)
            print('Please configurate \'config.json\' and run script again.')
            exit()
    vkHandler = vk_wrapper(**config)

def sequence_generator():
    number = 0
    while True:
        yield number
        number += 1

def get_img_request_handler(command):

    landscape_dict = set(['landscape', 'land', 'l', 'wide', 'w'])
    portrait_dict = set(['portrait', 'port', 'p', 'high'])

    def handle_command(obj, command):
        pic = Image.open(obj)
        width, height = pic.size
        if width > height and command in portrait_dict:
            pic = pic.transpose(Image.ROTATE_270)
        elif width < height and command in landscape_dict:
            pic = pic.transpose(Image.ROTATE_90)
        pic.save(obj)

    def handler(dir):
        imgs = sum(list(map(lambda t: ['{}/{}'.format(t,file) for file in os.listdir(dir+"/"+t) if os.path.isfile('{}/{}/{}'.format(dir,t,file))], [directory for directory in os.listdir(dir) if os.path.isdir(dir+"/"+directory)])), [])
        arch_path = dir+"/arch.zip"
        print("handling img request | dir: ", dir)
        with zipfile.ZipFile(arch_path, "w") as archive:
            for img in imgs:
                #handle_command(dir+"/"+img, command)
                archive.write(dir+"/"+img, img)
        return arch_path

    return handler

def img_names_generator():
    for name in sequence_generator():
        yield str(name)+".jpg"

def download_file(kwargs):
    if kwargs['type'] in ['photo', 'doc']:
        resp = requests.get(kwargs['url'])
        if not os.path.isdir(kwargs['path']):
            os.mkdir(kwargs['path'])
        if kwargs['name'].endswith('.'):
            kwargs['name'] += 'jpg'
        with open(kwargs['path'] + "/" + str(kwargs['name']), "wb") as writer:
            writer.write(resp.content)

    elif kwargs['type'] == 'video' and kwargs['url'] is not None:
        if kwargs['name'].endswith('.'):
            kwargs['name'] += 'mp4'
        ydl_opts = {'outtmpl': kwargs['path'] + "/" + str(kwargs['name']), 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([kwargs['url']])

def download_files(attachments, path = ".", name_generator = sequence_generator()):
    pool = Pool(max(min(len(attachments), os.cpu_count() - 1), 1))
    attachments = [{
        'type': attachment['type'],
        'url': attachment['url'] if 'url' in attachment else ('https://vk.com/video{}_{}'.format(attachment['owner_id'], attachment['id']) if attachment['type'] == 'video' else None),
        'path': '{}/{}'.format(path,attachment['owner_id']),
        'name': attachment['title'] if "title" in attachment and "ext" in attachment and attachment['title'] is not None and attachment['ext'] is not None and attachment['title'].lower().endswith("."+attachment['ext'].lower()) else ('{}.{}'.format(attachment['title'],attachment['ext']) if "title" in attachment and "ext" in attachment and attachment['title'] is not None and attachment['ext'] is not None else ('{}.'.format(attachment['title']) if 'title' in attachment and attachment['title'] is not None else '{:%Y-%m-%d_%H:%M:%S}_{}.'.format(datetime.fromtimestamp(attachment['date']), attachment['id'])))
        } for attachment in attachments]
    pool.map(download_file, attachments)
    pool.close()
    pool.join()

def bot_loop():
    print("Bot loop started.")
    for event in vkHandler.listen():
        if event.type == vkHandler.longpoll.VkBotEventType.MESSAGE_NEW:
            attachments, command, message_id = vkHandler.get_attachments(), vkHandler.get_command(), vkHandler.get_message_id()
            request_id = str(generate_id())
            request_dir = "userData/" + request_id
            os.mkdir(request_dir)

            try:
                request_handler = get_img_request_handler(command)
                vkHandler.send_message('downloading attachments...', reply_to = message_id)
                download_files(attachments, request_dir, img_names_generator())
                vkHandler.send_message('processing files...', reply_to = message_id)
                arch_path = request_handler(request_dir)
                vkHandler.send_message('uploading archive...', reply_to = message_id)
                vkHandler.send_message(attachment = arch_path, reply_to = message_id)

            except BaseException as e:
                vkHandler.send_message("An error occurred while processing your request.\n"+str(e),
                        reply_to = message_id)

            finally:
                shutil.rmtree(request_dir)

def main():
    init()
    print("Bot successfully initialized. Starting bot loop.")
    while True:
        try:
            sleep(1/10)
            bot_loop()
        except BaseException as e:
            print(e)
            print("An error occurred during events processing. Restarting...")
            sleep(1/10)

if __name__ == '__main__':
    main()



