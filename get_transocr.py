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
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from random import randint

log = logging.getLogger(__name__)

def sendmessage(message, username):
    data = {}
    data["email"] = "%s@rd.netease.com" %  username
    data["message"] = message
    url = "http://ci.corp.youdao.com/jenkins/job/NotifyPOPO/buildWithParameters"
    response = (urllib.request.urlopen(url, data=urllib.parse.urlencode(data).encode("utf-8")).read()).decode("utf-8")
    print(response)

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
    """
    python2 未改造
    """

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
        #m1.update(sign)
        sign = m1.hexdigest()
        url_data['sign'] = sign
        print(urlencode(url_data).encode('utf-8'))
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

class ZhiyunTransOCR(TRANSOCR):
    def authentication(self, authtype="online"):
        AppKey = "4fdd704eb21a9fdd"
        AppSecret = "FlgscR58gtGJHjkQw6N0hydxTyRrFquH"
        if authtype == "test":
            AppKey = "zhudytest123"
            #AppSecret = "IoyvG6Zb98nEUA4nIGwkEPUXILBYgrGs"
            AppSecret = "youdaoapiv120171"
        return {"appkey":AppKey, "appsecret":AppSecret}

    def truncate(self, q):
        if q is None:
            return None
        size = len(q)
        return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]


    def encrypt(self, signStr):
        hash_algorithm = hashlib.md5()
        hash_algorithm.update(signStr.encode('utf-8'))
        return hash_algorithm.hexdigest()

    def get_transocr(self, imgfile):
        authtype = "test"
        url = self.testhost
        if url is None:
            url = "https://openapi.youdao.com/ocrtransapi"
            authtype = "online"
        print(url)
        auth = self.authentication(authtype)
        appkey = auth['appkey']
        appsecret = auth['appsecret']

        imgb64 = self.get_img_base64(imgfile)

        data = {}
        data['from'] = self.lanfrom
        data['to'] = self.lanto
        data['type'] = '1'
        data['q'] = imgb64
        salt = str(uuid.uuid1())
        signStr = appkey + imgb64 + salt + appsecret
        sign = self.encrypt(signStr)
        print(sign)
        data['appKey'] = appkey
        data['salt'] = salt
        data['sign'] = sign
        data['res'] = 'composite' 

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=data, headers=headers)
        print(response.content)
        filename = os.path.splitext(os.path.split(imgfile)[-1])[0]
        resultfile = os.path.join(self.resultdir, filename + ".txt")
        json_file = os.path.join(self.resultdir, filename + ".json")
        f_out = open(resultfile, 'w', encoding="utf-8")
        try:
            jres = response.json()
            with open(json_file, 'w') as jf:
                json.dump(jres, jf)
            for region in jres["resRegions"]:
                f_out.write("%s\n%s\n\n" % (region['context'], region['tranContent']))
        except:
            log.exception(response.json())
            raise
        finally:
            f_out.close()

class ZhiyunRenderTransOCR(ZhiyunTransOCR):
    def get_transocr(self, imgfile):
        filename = os.path.splitext(os.path.split(imgfile)[-1])[0]
        resultfile = os.path.join(self.resultdir, filename + ".txt")
        json_file = os.path.join(self.resultdir, filename + ".json")
        render_file = os.path.join(self.resultdir, os.path.basename(imgfile))
        if os.path.isfile(resultfile) and os.path.getsize(resultfile) > 0:
            log.warn("img[%s] already get result!" % filename)
            return
        authtype = "test"
        url = self.testhost
        if url is None:
            #url = "http://ocr-trans.inner.youdao.com/ocrtransapi"
            #authtype = "test"
            url = "https://openapi.youdao.com/ocrtransapi"
            authtype = "online"
        auth = self.authentication(authtype)
        print(url, auth['appkey'])
        appkey = auth['appkey']
        appsecret = auth['appsecret']

        imgb64 = self.get_img_base64(imgfile)

        data = {}
        data['from'] = self.format_language_code(self.lanfrom)
        data['to'] = self.format_language_code(self.lanto)
        data['type'] = '1'
        data['appKey'] = appkey
        data['angle'] = '1'
        data['render'] = '1'
        data['res'] = 'composite'
        data['renderFallback'] = 'false'
        salt = str(uuid.uuid1())
        print(data)
        data['q'] = imgb64
        signStr = appkey + imgb64 + salt + appsecret
        sign = self.encrypt(signStr)
        #print(sign)
        data['salt'] = salt
        data['sign'] = sign
        data = urlencode(data).encode('utf-8')
        #print(data)
        param = {'s':data, 'et':2}
        response = requests.post(url, data=param)
        #print(res.content)
        try:
            jres = response.json()
            with open(json_file, 'w') as jf:
                json.dump(jres, jf)
            if 'render_image' in jres:
                imgdata = base64.b64decode(jres['render_image'])
                with open(render_file, 'wb') as f:
                    f.write(imgdata)
            with open(resultfile, 'w', encoding="utf-8") as f_out:
                for region in jres["resRegions"]:
                    f_out.write("%s\n%s\n\n" % (region['context'], region['tranContent']))
        except:
            traceback.print_exc()
            log.exception(response.content)
            raise

class TencentTransOCR(TRANSOCR):
    '''腾讯图片翻译'''
    __secret = [
        ("AKIDEG3f4F1uNbaKvLDdPwEG2f7JGxOaLCk5", "ECuNbZHpFPJxNWP2yiCQOL3VifOs65rz"),  # lichangying
        ("AKIDAA0czNiG2lJMAk6zJWZLx3vc3bv4krBo", "kGWYqOgzFK9oIXbUEk020A9jpIWYWHE8"),  # gongsisi
        ("AKIDAA0czNiG2lJMAk6zJWZLx3vc3bv4krBo", "kGWYqOgzFK9oIXbUEk020A9jpIWYWHE8"),  # zhangxiaolu
    ]
    __language = {
        'en': 'en',
        'cn': 'zh'
    }

    class FileSizeExceedLimit(Exception):
        '''自定义异常类，超出限制大小'''

        def __init__(self, message, status):
            super().__init__(message, status)
            self.message = message
            self.status = status

    class NotSuportLanguage(Exception):
        '''自定义异常类， 不支持语种'''

        def __init__(self, message, status):
            super().__init__(message, status)
            self.message = message
            self.status = status

    def trans_langcode(self, language, reverse=False):
        '''转化语言代码，提供反转换'''
        if reverse:
            for key, value in TencentTransOCR.__language.items():
                if value == language:
                    return key
        else:
            return TencentTransOCR.__language[language]

    def create_client(self):
        '''
        创建credential client，一次创建，长期使用，一个文件可以创建一次
        :return: client
        '''
        rand_digit = randint(0, 2)
        rand_digit = 0 # 测试用
        cred = credential.Credential(TencentTransOCR.__secret[rand_digit][0],
                                     TencentTransOCR.__secret[rand_digit][1])
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.signMethod = "TC3-HMAC-SHA256"
        clientProfile.httpProfile = httpProfile
        client = tmt_client.TmtClient(cred, "ap-beijing", clientProfile)
        return client

    def get_transocr(self, imgfile):
        '''
        请求图片翻译结果，首先对文件大小进行判断，不符合就返回 < 4M
        :param audioFormat:
        :return:
        '''
        fsize = os.path.getsize(imgfile)
        if fsize >= 4 * 1024 * 1024:
            log.exception("Image file size voer 4M")
            raise TencentTransOCR.FileSizeExceedLimit("Image file size voer 4M", 4301)

        # create client
        client = self.create_client()
        nonce = str(uuid.uuid1())
        # 转换语言代码
        try:
            # self.lanfrom = self.trans_langcode(self.lanfrom)
            # self.lanto = self.trans_langcode(self.lanto)
            
            self.lanfrom = self.format_language_code(self.lanfrom, TencentTransOCR.__language)
            self.lanto = self.format_language_code(self.lanto, TencentTransOCR.__language)
        except:
            log.exception('Current only support language is %s' % ' '.join(TencentTransOCR.__language.keys()))
            raise TencentTransOCR.NotSuportLanguage("Languag is not support", 4302)

        # 构建请求
        self.tencent_ocrtrans_req(client, imgfile, self.lanfrom, self.lanto, nonce)

    def tencent_ocrtrans_req(self, client, imgfile, fromLan, toLan, nonce):
        '''构建请求
        :param client:
        :param imgfile: img data, base64 encode
        :param fromLan: en or zh
        :param toLan: zh or en
        '''
        req = models.ImageTranslateRequest()
        params = '{"Action":"ImageTranslate", "Version":"2018-03-21", "Region":"ap-beijing",' \
                 '"SessionUuid":"%s", "Scene":"doc", "Data": "%s", "Source":"%s", "Target":"%s", "ProjectId": 0}' \
                 % (nonce, self.get_img_base64(imgfile), fromLan, toLan)
        log.info(imgfile)
        #log.info(params)
        # 将params参数字符串转为json
        req.from_json_string(jsonStr=params)
        # 发起请求
        try:
            resp = client.ImageTranslate(req)
            # 解析响应结果
            j_resp = resp.to_json_string()
            j_resp = json.loads(j_resp) # 转为json格式方便后续提取内容
        except TencentCloudSDKException as err:
            log.exception(err)
            # traceback.print_exc()
            raise err
        '''
        # 解析响应结果，关键信息需要整理成统一格式，其他字段信息可以原样留存
        log.info(j_resp)
        response_content = {}
        response_content['uuid'] = j_resp['SessionUuid']
        response_content['from'] = self.trans_langcode(j_resp['Source'], reverse=True)
        response_content['to'] = self.trans_langcode(j_resp['Target'], reverse=True)
        response_content['requestid'] = j_resp['RequestId']
        # 腾讯目前不包含组段信息，所以暂时认为属于一个大组段，位置信息设为0000
        response_content['content'] = []
        '''
        filename = os.path.splitext(os.path.split(imgfile)[-1])[0]
        resultfile = os.path.join(self.resultdir, filename + ".txt")
        json_file = os.path.join(self.resultdir, filename + ".json")
        # 将响应结果保存在json文件中
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(j_resp, f)
        # 将识别结果和翻译结果放在指定文件中
        try:
            # 提取原文和翻译文本
            srctext = []
            transtext = []
            for item in j_resp["ImageRecord"]["Value"]:
                srctext.append(item["SourceText"])
                transtext.append(item["TargetText"])
            log.debug(srctext, transtext)
            text_length = len(srctext) - 1
            with open(resultfile, 'w', encoding="utf-8") as f_out:
                for index, con in enumerate(srctext):
                    if index == text_length:
                        f_out.write("%s\n%s" % (con, transtext[index]))
                    else:
                        f_out.write("%s\n%s\n\n" % (con, transtext[index]))
        except:
            log.exception(traceback.format_exc())
            raise
        finally:
            time.sleep(0.2) # 每秒五次请求


class SougouTransOCR(TRANSOCR):
    '''搜狗图片翻译OCR'''
    __url = 'http://deepi.sogou.com/api/sogouService'
    __secret = [
        # (pid, key/secret)
        ('52db1895b60c5a55ed5322d1b5fec684', '83ddd3234bc46e153f69a445b0b0981d')    # lichangying
    ]
    __language = {
        'cn': 'zh-CHS',
        'en': 'en',
        'jp': 'ja',
        'ko': 'ko',
        'ru': 'ru',
        'fr': 'fr',
        'de': 'de',
        'sp': 'es',
        'pt': 'pt'
    }

    def md5(self, data):
        m = hashlib.md5()
        m.update(data.encode("utf-8"))
        return m.hexdigest()

    def trans_langcode(self, language, reverse=False):
        '''转化语言代码，提供反转换'''
        if reverse:
            for key, value in SougouTransOCR.__language.items():
                if value == language:
                    return key
        else:
            return SougouTransOCR.__language[language]

    def get_transocr(self, imgfile):
        rand_digit = randint(0, 2)
        rand_digit = 0  # 测试用
        # 平台PID 用户密钥
        pid, user_secret = SougouTransOCR.__secret[rand_digit]
        # 平台Service
        service = 'translateOpenOcr'
        # 随机数，自己随机生成，建议时间戳
        salt = str(int(time.time()))  # 10位时间戳
        # 图片base64编码
        img_base64_data = self.get_img_base64(imgfile)
        # sign签名
        # 若编码后数据长度超1024，取前1024位，否则，全取
        img_short_data = img_base64_data[0:1024] if len(img_base64_data) >1024 else img_base64_data
        sign = self.md5(pid + service + salt + img_short_data + user_secret)
        log.info(imgfile)
        log.info(sign)
        # 对各字段做URL encode
        data = {
            'service': service,
            'pid': pid,
            'salt': salt,
            'from': self.format_language_code(self.lanfrom, SougouTransOCR.__language),
            'to': self.format_language_code(self.lanto, SougouTransOCR.__language),
            'image': img_base64_data,
            'sign': sign
        }
        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'accept': "application/json"
        }
        # 建立请求
        try:
            res = requests.post(url=SougouTransOCR.__url, data=data, headers=headers)
            j_resp = json.loads(res.text)
            '''文本解析，整合组段信息'''
        except:
            log.exception(traceback.format_exc())
            raise
        # 将请求结果写入指定文件中
        filename = os.path.splitext(os.path.split(imgfile)[-1])[0]
        resultfile = os.path.join(self.resultdir, filename + ".txt")
        json_file = os.path.join(self.resultdir, filename + ".json")
        # 将响应结果保存在json文件中
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(j_resp, f)
        # 将识别结果和翻译结果放在指定文件中
        f_out = open(resultfile, 'w', encoding="utf-8")
        try:
            # 提取原文和翻译文本
            srctext = []
            transtext = []
            for item in j_resp["result"]:
                srctext.append(item["content"])
                transtext.append(item["trans_content"])
            log.debug(srctext, transtext)
            text_length = len(srctext) - 1
            for index, con in enumerate(srctext):
                if index == text_length:
                    f_out.write("%s\n%s" % (con, transtext[index]))
                else:
                    f_out.write("%s\n%s\n\n" % (con, transtext[index]))
        except:
            log.exception(traceback.format_exc())
            raise
        finally:
            f_out.close()
        time.sleep(0.2)  # 每秒五次请求



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
    # sendmessage("task done! 产品:%s, 语言方向:%s译%s, 结果地址:%s" %
    #         (args.product, args.lanfrom, args.lanto, args.outputdir), args.popouser)
