#coding=utf-8

import os
import sys
import signal


from config import Config
from storage import Oss
from storage import Task
from storage import AnnounceSql
from simple_pdf2html import *

switch_on = True 
def sig_handler(sig, frame):
    global switch_on
    switch_on = False
    print 'signal: kill'



task_name = sys.argv[1]
task = Task()
oss = Oss(task_name)
ann_sql = AnnounceSql()

signal.signal(signal.SIGTERM, sig_handler)
while switch_on:
    oss_pdf = task.get_task()
    if oss_pdf is not None:
        # 下载 pdf
        pdf_storage_path = os.path.join(Config.PDF_STORAGE_DIR, oss_pdf)
        print 'downloading :%s'% oss_pdf
        if oss.download(oss_pdf, pdf_storage_path):
            # 解析 pdf -> json
            with simplePDF2HTML(pdf_storage_path, task_name) as wizard: # 向魔法一样转换
                bias = [2, 3]  # [[2, 3], [1.5, 2], [3, 5]]
                wizard.convert(bias)
                if wizard.success:
                    # 保存 json -> oss
                    oss.upload(wizard.json_path)
                    # 写 oss_json -> mysql
                    ann_sql.update_item(oss_pdf)
                    print 'finish mysql update: %s'%oss_pdf
        #完成一个pdf 的转换
