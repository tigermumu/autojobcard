# -*- coding: utf-8 -*-
# @File   :
# @Info   :
# @Author : ZJ
# @Time   : 2025/7/7 14:18
import json
import logging
import os
import re
import time
from datetime import datetime

import requests
import xlrd




def setup_logger():
    log_dir = 'log'
    os.makedirs(log_dir, exist_ok=True)
    # 使用当前日期作为日志文件名
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'{current_date}.log')

    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 设置日志级别

    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建 FileHandler（不再需要 Rotating）
    handler = logging.FileHandler(
        filename=log_file,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)

    console_handle = logging.StreamHandler()
    console_handle.setLevel(logging.INFO)
    console_handle.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(handler)
    logger.addHandler(console_handle)
    return logger


log = setup_logger()


def getACInfo(txtACNO):
    # url = 'http://10.240.2.131:9080/trace/nrc/getACInfo.jsp?txtACNO=A6-EEG'
    url = f'http://10.240.2.131:9080/trace/nrc/getACInfo.jsp?txtACNO={txtACNO}'
    while True:
        try:
            result = requests.get(url, headers=headers, timeout=10)
            txt = result.text.strip()
            for i in json.loads(txt[1:-1]):
                print(i)
                return i
        except Exception as e:
            print(e)
            time.sleep(1)


def engAddSend(data):
    url = 'http://10.240.2.131:9080/trace/nrc/eng/engAddSend.jsp'
    try:
        result = requests.post(url, headers=headers, data=data, timeout=10)
        NRC_NO = re.search('NRC NO: (.+?) !', result.text).group(1)
        log.info(f'--->>开卡成功 {NRC_NO}  {data}')
    except Exception as e:
        print(e)
        log.error(f'--->>开卡失败 {data}')
        time.sleep(1)


def getJCEng(q):
    """
    获取 refNo
    :return:
    """
    url = 'http://10.240.2.131:9080/trace/nrc/eng/getJCEng.jsp'
    data = {
        # 'q': '80PANEL-340-1', 'limit': '20', 'timestamp': '1751874625719', 'txtWO': '120000550073'
        'q': q, 'limit': '20', 'timestamp': '1751874625719', 'txtWO': '120000550073'
    }
    while True:
        try:
            result = requests.post(url, headers=headers, data=data)
            refNo = result.text.strip().split(" ")[0]
            return refNo
        except Exception as e:
            print(e)
            time.sleep(1)









