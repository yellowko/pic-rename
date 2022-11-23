from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
import msrest

import os
import time
import re
from PIL import Image
import shutil
import sys


"""
此部分需要用户自定义
在Azure创建“认知服务-计算机视觉”后可以获取到自己的密钥和终结点
"""
subscription_key = "xxxxxxxxxxxxxxxxxxxx"   # 密钥
endpoint = "https://xxxxxxxxxx.cognitiveservices.azure.com/" #终结点
pic_path = r'D:\共享\我的表情包'   # 表情包文件夹路径，改成自己的
freq = 8 # 按照自己订阅类型提供的调用频率，S1订阅可提供10调用/秒

# 非法字符替换函数
def clean_file_name(filename:str):  
    q = '[?]'
    q_re = '问号'
    filename = re.sub(q,q_re,filename)
    invalid_chars='[\\\/:*"<>|]'
    replace_char='-'
    return re.sub(invalid_chars,replace_char,filename)

# @水印去除
def clean_watermark(text:str):
    reg = '^[\s\S]{0,5}@[\s\S]*'    # XX@XXX水印去除
    reg1 = '([a-zA-Z0-9][-a-zA-Z0-9]{0,62}\.)?[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.)([a-zA-Z0-9][-a-zA-Z0-9]{0,62})*'       # (XX.)XX.XX网址去除
    if re.match(reg, text, flags=0):
        return True
    elif re.match(reg1, text, flags=0):
        return True
    else:
        return False

# 文件重命名
def pic_rename(used_name:str,pic_path:str,midpath:str,title:str,pic_type:str):
    title = title[0:200] # 限制文件名长度
    try:
        new_name = pic_path + midpath + title + "." + pic_type
        os.rename(used_name, new_name)
    except FileExistsError:
        tail = 1
        new_name = pic_path + midpath + title + "_" + str(tail) + "." + pic_type
        while(os.path.exists(new_name)):
            tail += 1
            new_name = pic_path + midpath + title + "_" + str(tail) + "." + pic_type
        os.rename(used_name, new_name)

def my_mkdir(path:str):
    isExists=os.path.exists(path)
    if not isExists:
        os.mkdir(path)

computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))
filename_list = os.listdir(pic_path)  # 文件名读取

index = 0
failed = 0
named = 0
unnamed = 0
unsupport = 0
succeed = 0
num=len(filename_list)
read_image = 0
title = ''
time_delay = 1/freq

my_mkdir(pic_path+'\\unnamed.res\\')
my_mkdir(pic_path+'\\unsupport.res\\')
my_mkdir(pic_path+'\\named.res\\')
my_mkdir(pic_path+'\\failed.res\\')
my_mkdir(pic_path+'\\temp.res\\')

for i in filename_list:
    try:
        used_name = os.path.join (pic_path , filename_list[index])
        pic_type = i.split('.')[-1]
        
        if pic_type == 'gif' or pic_type == 'jpg' or pic_type == 'jpeg' or pic_type == 'png' or pic_type == 'bmp' or pic_type == 'pdf' or pic_type == 'tiff':
            read_image = open(used_name, "rb")
            if pic_type == 'gif':
                read_image = Image.open(used_name)
                read_image.seek(0)
                read_image.save(pic_path + '\\temp.res\\' + i.split('.')[-2] + '.png')
                read_image = open((pic_path + '\\temp.res\\' + i.split('.')[-2] + '.png'),'rb')

            # Call API with image and raw response (allows you to get the operation location)
            read_response = computervision_client.read_in_stream(read_image, raw=True)
            # Get the operation location (URL with ID as last appendage)
            read_operation_location = read_response.headers["Operation-Location"]
            # Take the ID off and use to get results
            operation_id = read_operation_location.split("/")[-1]

            # Call the "GET" API and wait for the retrieval of the results
            while True:
                time.sleep(time_delay) 
                read_result = computervision_client.get_read_result(operation_id)
                if read_result.status.lower () not in ['notstarted', 'running']:
                    break

            # Print results, line by line
            if read_result.status == OperationStatusCodes.succeeded:
                for text_result in read_result.analyze_result.read_results:
                    if len(text_result.lines)!=0:
                        title = ''
                        for line in text_result.lines:
                            if not clean_watermark(line.text):
                                title = title + line.text
                        title=clean_file_name(title)
                        read_image.close()
                        if title != '':
                            pic_rename(used_name,pic_path,'\\named.res\\',title,pic_type)
                            named += 1
                        else:
                            pic_rename(used_name,pic_path,'\\unnamed.res\\',i.split('.')[-2],pic_type)
                            unnamed += 1
                    else:
                        read_image.close()
                        pic_rename(used_name,pic_path,'\\unnamed.res\\',i.split('.')[-2],pic_type)
                        unnamed += 1
        elif pic_type == 'res':
            index += 1
            continue
        else:
            pic_rename(used_name,pic_path,'\\unsupport.res\\',i.split('.')[-2],pic_type)
            unsupport += 1

        succeed += 1
    except msrest.exceptions.ClientRequestError:
        print("\n客户端连接失败，请检查自己的网络连接情况，如果有代理请关闭\n")
        sys.exit()
    except Exception:
        # print("Unexpected error:", sys.exc_info()[0])
        if read_image:
            read_image.close()
        pic_rename(used_name,pic_path,'\\failed.res\\',i.split('.')[-2],pic_type)
        failed += 1
    index += 1
    print("\r已完成 %.2f %%" %(100*index/num),end='')
        
shutil.rmtree(pic_path+'\\temp.res\\')
print("\n处理了" + str(num-4) + "张图片，重命名" + str(named) + "张，无字" + str(unnamed) + "张，不支持" + str(unsupport) + "张，失败" + str(failed) + "张\n")
if failed:
    print("存在失败的文件，失败的文件可能尺寸过小\n")