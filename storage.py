#!/Users/kevinhuang/mpython/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import redis
import MySQLdb
import oss2
from log import Log

from config import Config

class Oss(object):
    def __init__(self, task_name):

        access_key_id = os.getenv('OSS_TEST_ACCESS_KEY_ID', Config.OSS_TEST_ACCESS_KEY_ID)
        access_key_secret = os.getenv('OSS_TEST_ACCESS_KEY_SECRET', Config.OSS_TEST_ACCESS_KEY_SECRET)
        bucket_name = os.getenv('OSS_TEST_BUCKET', Config.OSS_TEST_BUCKET)
        endpoint = os.getenv('OSS_TEST_ENDPOINT', Config.OSS_TEST_ENDPOINT)
        # 创建Bucket对象，所有Object相关的接口都可以通过Bucket对象来进行
        self.bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)
        self.logger = Log(Config.LOG_DIR, task_name)

    def upload(self, file_path):
        try:
            code = file_path.split('/')[-2]
            remote_key = os.path.join('announcement_json', code, os.path.basename(file_path))
            with open(file_path, 'rb') as f:
                self.bucket.put_object(remote_key, f) # 上传文件
            return True
        except Exception, ex:
            self.logger.log(4, file_path, ex)
            return False

    def download(self, remote_path, store_path):
        try:
            code = remote_path.split('/')[-2]
            if not os.path.exists(os.path.dirname(store_path)):
                os.makedirs(os.path.dirname(store_path))
            self.bucket.get_object_to_file(remote_path, store_path)
            if not os.path.exists(store_path):
                raise Exception('oss file: %s not exitsts'%remote_path)
            return True
        except Exception, ex:
            self.logger.log(4, remote_path, ex)
            return False

class AnnounceSql(object):
    def __init__(self):
        self.conn = None

    def ensure_connection(self):
        if self.conn is None:
            self.conn = MySQLdb.connect(host=Config.ANN_HOST, port=Config.ANN_PORT,
                user=Config.ANN_USER, passwd=Config.ANN_PASSWORD, db=Config.ANN_DB)
        else:
            self.conn.ping(True)

    def update_item(self, oss_pdf):
        code = oss_pdf.split('/')[-2]
        basename = os.path.basename(oss_pdf)
        pdf_oss_path= os.path.join('announcement', code, basename)
        json_oss_path = os.path.join('announcement_json', code, basename[:-3] + 'json')
        self.ensure_connection()
        cur = self.conn.cursor()
        sql = 'update announcement SET json_url=\'%s\' where oss_url=\'%s\'' % (json_oss_path, pdf_oss_path)
        print sql
        cur.execute(sql)
        cur.close()
        self.conn.commit()


class Task():

    def __init__(self):
        self.redis_conn = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, password=Config.REDIS_PASSWD \
                                , db= Config.REDIS_DB, decode_responses=True)
        self.sleep_sec = 0 # 控制访问速度

    def get_task(self):
        # 打印 info, 下边可能会阻塞
        time.sleep(self.sleep_sec)
        task = self.redis_conn.spop(Config.REDIS_SET_NAME)
        if task is not None: # 控制redis的 请求速度
            self.sleep_sec = 0
        else:
            self.sleep_sec = 10
        return task

