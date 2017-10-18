#coding=utf-8

import os
import sys
import gc
import operator


reload(sys)
sys.setdefaultencoding('utf8') #设置默认编码

from log import Log

class PDF2HTML(object):
    def __init__(self, pdf_path, html_path, password="", codec='utf-8', bias_param=[1.5, 2]):
        self.pdf_path = pdf_path
        self.html_path = html_path
        self.codec = codec
        self.bias_param = bias_param
        self.reader = open(pdf_path, 'rb')
        self.writer = open(html_path, 'w')  # 'a'
        self.json_path = os.path.join("/Users/kevinhuang/svn/pdfweb/pdfweb/resources/data/", os.path.basename(html_path).replace('html','json'))
        self.debug_log = open('debug.log', 'a')
        self.password = password
        self.device = None
        self.indent = '  '
        self.level = 0
        self.outlines = None
        self.outlines_dict = None

        self.debug_mode_on = False #True
        self.pages = []
        self.page_html = ""
        self.catalog_separator = ""
        self.subtitles = []
        self.curr_anchor_id = 1
        # http://webdesign.about.com/od/styleproperties/p/blspfontweight.htm
        self.fontweight_dict = {
            self.chinese_str('ABCDEE+黑体'): 'bold',
            self.chinese_str('ABCDEE+宋体'): 'normal'
        }
        self.endmark_list = [
            self.chinese_str('：'),
            self.chinese_str(':'),
            self.chinese_str('。'),
            self.chinese_str('？'),
            self.chinese_str('?'),
            self.chinese_str('！'),
            self.chinese_str('!'),
            self.chinese_str('；')
        ]
        self.logger = Log('./data2', 'task1.log')
    # print "init"
    def __enter__(self):
        # print "enter"
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # print "exits"
        return
    def __del__(self):
        # print "deleted"
        self.reader.close()
        self.writer.close()
        self.debug_log.close()
        if self.device:
            self.device.close()
        sys._clear_type_cache()
        gc.collect()

    def write(self, content, body=False):
        if body:
            self.page_html += content
        try:
            self.writer.write(self.level * self.indent + str(content) + '\n')
        except Exception, ex:
            pass


    def is_catalog(self, content):


        catalog_base_word = {u'第': '', u'章': '', u'节': '',
                             u'一': 1, u'二': 2, u'三': 3, u'四': 4, u'五': 5,
                             u'六': 6, u'七': 7, u'八': 8, u'九': 9, u'十': 10
                             }

        candidate_space = content.split(' ')[0].decode('utf-8')
        if len(candidate_space) >= 3: # 第一章
            is_space_title = True
            for c in candidate_space:
                if c not in catalog_base_word:
                    is_space_title = False
                    break
            if is_space_title is True:
                #if len(self.subtitles) == 0:
                self.catalog_separator = " "
                self.subtitles.append({'stName': content,
                                       'anchorId': "p{0}".format(self.curr_anchor_id), 'sub': []})
                return True

        candidate_dayton = content.split('、')[0].decode('utf-8')
        if len(candidate_dayton) >= 1: # 一
            is_dayton_title = True
            for c in candidate_dayton:
                if c not in catalog_base_word:
                    is_dayton_title = False
                    break
            if is_dayton_title is True:
                if self.catalog_separator is " ":
                    self.subtitles[-1]['sub'].append({'stName': content,
                                                      'anchorId': "p{0}".format(self.curr_anchor_id)})
                else:
                    self.subtitles.append({'stName': content, 'anchorId': "p{0}".format(self.curr_anchor_id)})
                return True
        return False

    def write2(self, text, align, font_size, weight, indent, page_id=-1):

        content = text
        is_catalog = False
        if u'..........' in content:
            content_list = content.split(' ')
            catalog_list = []
            for item in content_list:
                catalog_list.append(item)
                catalog_list.append('&nbsp;')
                if item.isdigit():
                    catalog_list.append('<br>')
            content = ''.join(catalog_list)
        else:
            is_catalog = self.is_catalog(content) # 需要用字号, 排除一下干扰

        is_page_number = text.isdigit() and int(text) > 0

        if is_catalog or weight is not 'normal': # font_size > 12 or
            content = '<b>{0}</b>'.format(content)
        content = '{0}{1}'.format(int(indent)*'&emsp;', content)

        if is_catalog is True:
            content = '<p id="p{0}" align="{1}">{2}</p>'.format(self.curr_anchor_id, align, content)
            self.curr_anchor_id += 1
            if self.curr_anchor_id == 8:
                pass
            print self.curr_anchor_id
        else:
            content = '<p align="{0}">{1}</p>'.format(align, content)

        self.write(content, not is_page_number)

    def debug_write(self, content):
        self.debug_log.write(str(content).encode('utf-8') + '\n')

    def chinese_str(self, content, codec='utf-8'):
        #return u'{0}'.format(content).encode('gbk')
        return content.decode(codec).encode('gbk')

    def get_last_char(self, content):
        length = len(content)
        return content[length - 1:]

    def sort_dict_by_val(self, dictdata, reverse=True):
        return sorted(dictdata.items(), key=operator.itemgetter(1), reverse=reverse)

    def convert(self, bias_param=None):
        pass

    def writeHTML(self):
        pass
    def writeHead(self):
        pass
    def writeBody(self):
        pass