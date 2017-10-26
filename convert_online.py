#coding=utf-8

import os

from config import Config
from storage import Oss
from storage import Task
from storage import AnnounceSql
from simple_pdf2html import *


task = Task()
oss = Oss('test')
ann_sql = AnnounceSql()

while True:
    oss_pdf = task.get_task()
    if oss_pdf is not None:
        # 下载 pdf
        pdf_storage_path = os.path.join(Config.PDF_STORAGE_DIR, oss_pdf)
        if oss.download(oss_pdf, pdf_storage_path):
            # 解析 pdf -> json
            with simplePDF2HTML(pdf_storage_path) as wizard: # 向魔法一样转换
                bias = [2, 3]  # [[2, 3], [1.5, 2], [3, 5]]
                wizard.convert(bias)
                if wizard.success:
                    # 保存 json -> oss
                    oss.upload(wizard.json_path)
                    # 写 oss_json -> mysql
                    ann_sql.update_item(oss_pdf)
        #完成一个pdf 的转换

