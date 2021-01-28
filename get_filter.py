import json
import os
import pandas as pd
import time
import hashlib
import argparse
from urllib.parse import urlparse, parse_qs, urlencode
import requests

def get_trans(lanfrom,lanto,json_path,result_path):
    '''
    case:对应的图片 context：ocr识别结果，组段为单位，onlinecontext：线上过滤模型的结果  onlinetrans：线上翻译结果 textcontext：测试模型过滤结果 testtrans：测试模型翻译结果
    请求单位为OCR识别组段
    目前线上的过滤模型会对整句的某些字符进行过滤，返回的过滤结果是列表，所以对结果进行拼接
    测试的过滤模型已经不需要拼接，过滤结果为：过滤/不过滤
    '''
    df  = pd.DataFrame(columns=['case','context','onlinecontext','onlinetrans','testcontext','testtrans'])
    index = 0
    for j in os.listdir(json_path):
        if j.endswith('json'):
            print(json_path,j)
            with open(os.path.join(json_path,j),'r') as fp:
                data = json.load(fp)
                for d in data['resRegions']:
                    df.loc[index,'context'] = d['context']
                    df.loc[index,'case'] = j
                    index += 1
                fp.close()
            
    for con in zip(df.context,df.index):
        src = con[0]
        online_host = " http://dict.youdao.com/dictserver/translate"
        test_host = 'http://dict-test.youdao.com/dictserver/translate'
        data = {}
        data['i'] = src
        data['from'] = lanfrom
        data['to'] = lanto
        data['product'] = 'bilingual_contrast'
        secrete_key = "feature/language_contrast_pl"
        data['salt'] = 'test123'
        sign = data['product']+data['i']+data['salt']+secrete_key
        m1 = hashlib.md5(sign.encode('utf8'))
        data['sign'] = 'test123'

        test_res = requests.post(
            url = test_host,
            data = data
        )
        online_res = requests.post(
            url = online_host,
            data = data
        )
        try:
            test_res.encoding= 'utf-8'
            test_result =  test_res.json()
            #解析测试数据
            for i in test_result['translateResult']:
                text = ''
                trans = ''
                for s in i:
                    text+=s['src']
                    trans+=s['tgt']
                print(text,'\n','______________________','\n',trans)
                df.loc[con[1],'testtrans'] =trans
                df.loc[con[1],'testcontext'] =text
            #解析线上数据   
            online_result = online_res.json()
            for j in online_result['translateResult']:
                otext = ''
                otrans = ''
                for s in j:
                    otext+=s['src']
                    otrans+=s['tgt']
                df.loc[con[1],'onlinetrans'] =otrans
                df.loc[con[1],'onlinecontext'] =otext
            if test_result['code'] != "0":
                print("errorCode is %s" %  test_result['code'])
                raise
            if online_result['code'] != "0":
                print("errorCode is %s" %  online_result['code'])
                raise
        except:
            pass
    df.to_excel(os.path.join(result_path,'%s.xlsx'%(str(lanfrom)+'_'+str(lanto))))
    
def run(inputdir,resultdir):
    #互译的语言代码，需要增加或减少语言，在这里修改即可
    tar_lan = ['en','zh-CHS','ko','ja']
    for d in os.listdir(inputdir):
        json_path = os.path.join(inputdir,d)
        lanfrom = d.split('_')[0]
        lanto = d.split('_')[1]
        if lanfrom in tar_lan and lanto in tar_lan:
            print(lanfrom,lanto)
            get_trans(lanfrom,lanto,json_path,result_path=resultdir)
        
        
if __name__ == "__main__":
    curpath = os.getcwd()
    parser = argparse.ArgumentParser(description='Command line client for get stream result')
    parser.add_argument('-i', '--inputdir', default=os.path.join(curpath, "data/test_one"), dest="inputdir", help="OCR识别结果目录")
    parser.add_argument('-r', '--resulttdir', default=os.path.join(curpath, "result/test_one"), dest="resultdir", help="结果根目录")
    args = parser.parse_args()
    
    run(args.inputdir,args.resultdir)
