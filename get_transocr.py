import os
import sys
import urllib
import base64
import json
import argparse
import requests
import time
import traceback
import hmac
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode
import codecs
import uuid
import logging
from random import randint

log = logging.getLogger(__name__)


class TRANSOCR(object):
    def __init__(self, lanfrom, lanto, imgdir, resultdir, testhost=None):
        self.lanfrom = lanfrom
        self.lanto = lanto
        self.testhost = testhost
        self.imgdir = imgdir
        if not os.path.isdir(self.imgdir):
            log.exception("not find imgdir: %s" % imgdir)
        self.resultdir = resultdir
        if not os.path.isdir(self.resultdir):
            os.makedirs(self.resultdir)
        pass

    def authentication(self):
        pass

    def get_img_base64(self, img_file):
        with open(img_file, 'rb') as infile:
            s = infile.read()
        return base64.b64encode(s).decode('utf-8') 

    def format_language_code(self, language, special_language_code=None):
        if special_language_code is None:
            special_language_code = {
                'cn': 'zh-CHS',
                'jp': 'ja',
            }
        if language in special_language_code:
           return special_language_code[language]
        return language

    def get_transocr(self, imgfile):
        pass

    def crawler(self, failfile=None):
        faillist = []
        imglist = []
        if failfile is None:
            imglist = os.listdir(self.imgdir)
        else:
            f_fail = open(failfile, 'r')
            for line in f_fail:
                imglist.append(line.strip())
            f_fail.close()
        index = 0
        log.info("start to crawl images")
        log.info(imglist)
        imglist.sort()
        for img in imglist:
            imgfile = os.path.join(self.imgdir, img)
            if not os.path.isfile(imgfile):
                continue
            if img.startswith('.'):
                continue
            #time.sleep(0.5)
            for i in range(0, 3):
                try:
                    log.info("%s:%s" % (index, img))
                    self.get_transocr(os.path.join(self.imgdir, img))
                    break
                except:
                    traceback.print_exc()
                    faillist.append(img)
                    log.exception("Exception:\t%s" % img)
                    time.sleep(0.5)
            index += 1
        return faillist

class YoudaoTransOCR(TRANSOCR):

    def get_input_for_sign(self, img64):
        if len(img64) < 10:
            return ""
        first10 = img64[0:10]
        inputlen = len(img64)
        last10 = ""
        if inputlen <= 20:
            last10 = img64
        else:
            last10 = img64[-10:]
        return "%s%s%s" % (first10, inputlen, last10)

    def get_transocr(self, imgfile):
        imgb64 = self.get_img_base64(imgfile)
        test_host = "http://fanyi.youdao.com/ocr/tranocr"
        if self.testhost is not None:
            test_host = self.testhost
        url_data = {}
        url_data['clientele'] = "test"
        secrete_key = "youdaoapiv120171"
        url_data['keyfrom'] = "mdict.7.4.4.iphonepro"
        url_data['imei'] = "imei"
        url_data['salt'] = str(int(time.time()))
        url_data['from'] = self.lanfrom
        url_data['to'] = self.lanto
        sign = url_data['clientele'] + self.get_input_for_sign(imgb64) + url_data['salt'] + secrete_key 
        m1 = hashlib.md5(sign.encode('utf8'))
        sign = m1.hexdigest()
        url_data['sign'] = sign
        print(urlencode(url_data).encode('utf-8'))
        #url '&noCheckPrivate=true' 跳过验证，secrete_key已过期
        url = test_host + "?" + str(urlencode(url_data).encode('utf-8')).split("'")[1] + '&noCheckPrivate=true'
        print(url)
        response = requests.post(
            url = url,
            data = imgb64
        )
        filename = os.path.splitext(os.path.split(imgfile)[-1])[0]
        json_file = os.path.join(self.resultdir, filename + ".json")
        try:
            j_result =  response.json()
            print(j_result)
            print(self.lanfrom,self.lanto)
            if j_result['errorCode'] != "0":
                print("errorCode is %s" %  j_result['errorCode'])
                raise
            with open(json_file, 'w') as jf:
                json.dump(j_result, jf)
        except:
            print(response.content)
            raise


def run(lanfrom, lanto, inputdir, outputdir, failfile, testhost, loggername=None):

    if loggername is not None:
        global log
        log = logging.getLogger(loggername)
    m_ocr = YoudaoTransOCR(lanfrom, lanto, inputdir, outputdir, testhost)
    faillist = m_ocr.crawler(failfile)
    f = open(os.path.join(outputdir, "faillist.txt"), 'w')
    for fail_img in faillist:
        f.write("%s\n" % fail_img)
    f.close()
    
def get_result(testdir,resultdir):
'''
    适用的项目为 中文——其他语言互译
    测试集根目录下图片以本身语言代码命名：中文：cn；英文：en，日文：ja；韩文：ko
    测试结果为 lanfrom_lanto 格式命名的文件夹
'''
    for testdata in os.listdir(testdir):
        lanfrom = testdata
        inputdir = os.path.join(testdir,testdata)
        if lanfrom == 'cn':
            lantolist = os.listdir(testdir)
            lantolist.remove('cn')
            lanfrom = 'zh-CHS'
        else:
            lantolist =['zh-CHS']
        for lanto in lantolist:
            tgtdir = resultdir+'/'+lanfrom+'_'+lanto 
            outputdir = resultdir+'/'+lanfrom+'_'+lanto+'/'
            print(lanfrom,lanto)
            if not os.path.exists(outputdir):
                os.makedirs(outputdir)
            run(lanfrom,lanto,inputdir,outputdir,None,None,None)

        

if __name__ == "__main__":
    curpath = os.getcwd()
    loggername = "test"
    logfile = os.path.join(curpath, 'test.log')
    l = logging.getLogger(loggername)
    formatter = logging.Formatter('%(asctime)s-%(name)s-%(filename)s-%(funcName)s:%(lineno)s:%(levelname)s: %(message)s')
    fileHandler = logging.FileHandler(logfile, mode='a')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    l.setLevel(logging.INFO)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)

    parser = argparse.ArgumentParser(description='Command line client for get stream result')
    parser.add_argument('-i', '--inputdir', default=os.path.join(curpath, "data/test_one"), dest="testdir", help="测试集根目录")
    parser.add_argument('-o', '--outputdir', default=os.path.join(curpath, "result/test_one"), dest="resultdir", help="结果根目录")
    args = parser.parse_args()
    
    get_result(args.testdir,args.resultdir)

