#coding=utf-8

import re
import json
from pdfminer.layout import *
from table import TableFrame


class Line(object):

    def __init__(self, text, align, font_name, font_size, indent, num_chars, bot_left):
        self.text = text.strip()
        self.align = align
        self.font_size = font_size
        self.font_name = font_name.decode('gbk').encode('utf-8')
        self.indent = indent
        self.num_chars = num_chars
        self.left = bot_left[0]
        self.bot = bot_left[1] # TextLine的下边界
        # 目录
        self.is_subtitle = False
        self.page_no = None
        self.line_no = None

    def set_line_id(self, page_no, line_no):
        self.page_no = page_no
        self.line_no = line_no

    def anchor_id(self):
        return 'sub-{0}-{1}'.format(self.page_no, self.line_no)

    def set_subtitle(self, is_subtitle):
        self.is_subtitle = is_subtitle

    def is_new_para(self, min_indent, max_chars_in_a_line, last_l):

        if self.font_size != last_l.font_size: # 字号需相等
            return True
        if self.left == min_indent:
            # 除非此行比较短，否则认定为没有分段
            if self.num_chars/max_chars_in_a_line < 0.7:
                return True  # 顶到最有边，句子字符数，不及最多字符数的70%
            return False  # 顶到最有边，句子字符数，多于最多字符数的70% （近似认为句子顶到最右边）
        else:
            return True

    def directory_index_format(self, ):
        content = self.text.decode('utf-8')
        if u'..........' in content:
            res = re.findall(r'\d+', content)
            for s in res[::-1]:
                idx = content.find(s)
                content = content[:idx+len(s)] + '<br>\n' + content[idx+len(s):]
        return content.encode('utf-8')


    def dumps_to_html(self):

        content = self.directory_index_format()
        content = '{0}{1}'.format(int(self.indent) * '&emsp;', content)  #转成html 缩进

        anchor = ''
        if self.is_subtitle:  # font_size > 12 or
            content = '<b>{0}</b>'.format(content)
            anchor = 'id=\"{0}\" '.format(self.anchor_id())
        content = '<p {2}align="{0}">{1}</p>'.format(self.align, content, anchor)

        return content

    def is_bold(self):

        if 'Bold' in self.font_name or '黑体' in self.font_name:
            return True
        return False

    def is_sub_by_separator(self, separator):
        text_unicode = self.text.decode('utf-8')
        base_word = {u'第': '', u'章': '', u'节': '',
                u'一': 1, u'二': 2, u'三': 3, u'四': 4, u'五': 5,
                u'六': 6, u'七': 7, u'八': 8, u'九': 9, u'十': 10
                }

        if separator in text_unicode:
            phrase = text_unicode.split(separator)[0]
            if phrase is not '':
                is_subtitle = True
                for c in phrase:
                    if c not in base_word:
                        is_subtitle = False
                self.set_subtitle(is_subtitle)
                return is_subtitle

        return False

    def possible_subtitle(self):

        text_unicode = self.text.decode('utf-8')

        # 太长的 非加粗字体 排除
        if len(text_unicode) > 37:
            return False

        if self.is_sub_by_separator(u' ') or self.is_sub_by_separator(u'、'):
            return True

        return False


# pdf 页的内部表示
# page 应该表现为 多个段落的 list
# 一行 subtitle 是段落， 一个文本段落是段落, 一个表格是段落

class Page(object):
    def __init__(self, number, max_num_chars, min_indent, page_xrange):
        self.page_no = number
        self.elements = [] #line table
        self.paras = []
        self.min_indent = min_indent
        self.max_chars_in_a_line = max_num_chars
        self.page_xrange = page_xrange

    def add(self, obj):
        self.elements.append(obj)

    # 左对齐的时候， 或者同y0的时候 才考虑合并
    def merge_lines_to_paragraph(self):
        last_i = -1
        last_ele = None
        curr_para = None
        for i,ele in enumerate(self.elements):

            if isinstance(ele, TableFrame):
                if curr_para is not None:
                    self.paras.append(curr_para)
                    curr_para = None # 遇到 table 后 para 重新计算
                self.paras.append(ele)

            if isinstance(ele, Line):
                if curr_para is None:
                    curr_para = ele
                else:
                    if ele.is_new_para(self.min_indent, self.max_chars_in_a_line, self.elements[i-1]):
                        self.paras.append(curr_para)
                        curr_para = ele
                    else:
                        curr_para.text += ele.text

        if curr_para is not None:  #处理最后一个 para
            self.paras.append(curr_para)

        for i,para in enumerate(self.paras): #记录 行号 page 号等信息
            if isinstance(para, Line):
                self.paras[i].set_line_id(self.page_no, i)

    def dumps_to_html(self):  # 当前page生成html的str
        html = []
        last_text = None
        for i, para in enumerate(self.paras):
            if isinstance(para, TableFrame):
                html.extend(para.dumps_to_html(self.page_xrange))
            if isinstance(para, Line):
                if para.text != '':
                    html.append(para.dumps_to_html())
                    last_text = para.text
        if last_text is not None:
            if last_text.isdigit():
                del html[-1]

        return '\n'.join(html)

class Pdf(object):

    def __init__(self):
        self.pages = []
        self.raw_subtitles = []
        self.subtitles = []
        self.html_body = []

    def add(self, page):
        self.pages.append(page)


    def collect_possible_subtitle(self):
        # 搜集可能的 subtitle
        for page in self.pages:
            for para in page.elements:
                if isinstance(para, Line):
                    if para.possible_subtitle():
                        self.raw_subtitles.append(para)

    def max_i_key(self, i, d):
        return sorted(d.keys(),reverse=True)[i]

    def extract_subtitle(self):
        self.collect_possible_subtitle()
        # 合并第几章节，肯定是
        fonts = {}
        for i,para in enumerate(self.raw_subtitles):
            if round(para.font_size) not in fonts:
                fonts[para.font_size] = []
            fonts[para.font_size].append(i)
        top_raw_id = []
        for raw_id in fonts[self.max_i_key(0, fonts)]:
            sub = {}
            sub['stName'] = self.raw_subtitles[raw_id].text
            sub['anchorId'] = self.raw_subtitles[raw_id].anchor_id()
            sub['sub'] = []
            self.subtitles.append(sub)
            top_raw_id.append(raw_id)

        if len(fonts) > 1:
            top_raw_id.append(len(self.raw_subtitles)) #方便处理最后一个
            for i in range(0,len(top_raw_id)-1):
                for raw_id in range(top_raw_id[i]+1, top_raw_id[i+1]):
                    if raw_id in fonts[self.max_i_key(1, fonts)]: # 需要被拆分到 一级标题中去
                        second_sub = {}
                        second_sub['stName'] = self.raw_subtitles[raw_id].text
                        second_sub['anchorId'] = self.raw_subtitles[raw_id].anchor_id()
                        self.subtitles[i]['sub'].append(second_sub)

    def html_head(self):
        head = ['<head>']
        head.append('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">')
        head.append('<title>PDF格式转HTML</title>')
        head.append('</head>')
        return head

    def dumps_to_html(self):
        html = ['<!DOCTYPE html>']
        html.append('<html>')
        html.extend(self.html_head())
        # html_body
        if len(self.html_body) == 0: #第2次调用时，使用缓存
            for page in self.pages:
                self.html_body.append(page.dumps_to_html())
        html.extend(self.html_body)
        html.append('</html>')
        return '\n'.join(html)

    def dumps_to_json(self):
        res = {'Pages': []}
        for page in self.pages:
            res['Pages'].append({'PageNo': page.page_no + 1, 'PageContent': page.dumps_to_html()})
        res['SubTitles'] = self.subtitles
        return json.dumps(res, ensure_ascii=False)

