import requests
import os
import sys
import uuid
import hashlib
from importlib import reload
import base64
import json
filepath = r"C:\Users\asd\Desktop\test"
reload(sys)


YOUDAO_URL = 'https://openapi.youdao.com/ocrtransapi'
APP_KEY = '7c562ceb9e2f3286'
APP_SECRET = 'Z9nDyXeyctM3NewmPMITKOnxqxyoISX5'


def truncate(q):
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]


def encrypt(signStr):
    hash_algorithm = hashlib.md5()
    hash_algorithm.update(signStr.encode('utf-8'))
    return hash_algorithm.hexdigest()


def do_request(data):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    return requests.post(YOUDAO_URL, data=data, headers=headers)


def connect(path):
    f = open(path, 'rb')  # 二进制方式打开图文件
    q = base64.b64encode(f.read()).decode('utf-8')  # 读取文件内容，转换为base64编码
    f.close()

    data = {}
    data['from'] = 'zh-CHS'
    data['to'] = 'en'
    data['type'] = '1'
    data['q'] = q
    salt = str(uuid.uuid1())
    signStr = APP_KEY + q + salt + APP_SECRET
    sign = encrypt(signStr)
    data['appKey'] = APP_KEY
    data['salt'] = salt
    data['sign'] = sign

    response = do_request(data).json()
    image_txt = ''
    image_translate = ''

    for i in response.get('resRegions'):
        image_txt = image_txt +i['context']
        image_translate = image_translate + i['tranContent']
    print(image_txt,'\n',image_translate)




if __name__ == '__main__':
    for i in os.listdir(filepath):
        connect(os.path.join(filepath,i))
