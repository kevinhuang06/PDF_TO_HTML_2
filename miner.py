#coding=utf-8

from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import *


class Miner(object):
    def __init__(self, fname):
        self.fname = fname
        self.password = ""
        self.document = None
        self.device = None
        self.interpreter = None
        #存储所有页面
        self.miner_pages = []
        #考虑异常处理
        with open(self.fname) as f:
            self.parse(f)


    def parse(self, f):
        # 创建一个PDF文档解析器对象
        parser = PDFParser(f)
        # 创建一个PDF文档对象存储文档结构
        self.document = PDFDocument(parser, self.password)  #PDF 损坏后，此处抛异常
        # 检查文件是否允许文本提取
        if not self.document.is_extractable:
            raise PDFTextExtractionNotAllowed

        # 创建一个PDF资源管理器对象来存储共享资源
        rsrcmgr = PDFResourceManager()
        # 创建一个PDF页面聚合对象
        self.device = PDFPageAggregator(rsrcmgr, laparams=LAParams())  # 创建一个PDF设备对象
        # 创建一个PDF解析器对象
        self.interpreter = PDFPageInterpreter(rsrcmgr, self.device)
        for idx, miner_page in enumerate(PDFPage.create_pages(self.document)):




