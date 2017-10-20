#coding=utf-8

import re
import json
import sys

from pdfminer.layout import *
from table import TableFrame


class Line(object):

    def __init__(self, text, align, font_name, font_size, indent, num_chars, location):
        self.text = text.strip()
        self.align = align
        self.font_size = round(font_size) #四舍五入
        self.font_name = font_name
        self.indent = indent
        self.num_chars = num_chars
        self.left = location[0]
        self.right = location[1] # TextLine的右边界
        # 目录
        self.is_subtitle = False
        self.page_no = None
        self.line_no = None
        self.subtitle_id = None

    def set_line_id(self, page_no, line_no):
        self.page_no = page_no
        self.line_no = line_no

    def anchor_id(self):
        return 'sub-{0}-{1}'.format(self.page_no, self.line_no)

    def set_subtitle(self, is_subtitle):
        self.is_subtitle = is_subtitle


    def is_new_para(self, major_min_indent, max_chars_in_a_line, last_l):
        if self.possible_subtitle():
            return True
        #if self.font_size != last_l.font_size: # 字号需相等
        #    return True
        #if self.font_name != last_l.font_name:
        #    return True
        if self.left <= major_min_indent: # 文本靠左
            # 除非此行比较短，否则认定为没有分段
            if last_l.num_chars/max_chars_in_a_line < 0.9:
                return True  #上一行文本写满了
            return False  #
        else:#比major_min_indent 大的，说明前边有空白符，肯定不合并
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

    def is_sub_by_separator(self, separator):
        text_unicode = self.text.decode('utf-8')
        base_word = { u'一': 1, u'二': 2, u'三': 3, u'四': 4, u'五': 5,
                u'六': 6, u'七': 7, u'八': 8, u'九': 9, u'十': 10
                }
        if u'......' in text_unicode: # 丢弃掉 目录索引
            return False

        top_size = {u'章': 35, u'节': 30}

        if separator in text_unicode:
            phrase = text_unicode.split(separator)[0]
            if len(phrase) >=3: #有可能是 第x章， 第x节
                if u'第' == phrase[0] and phrase[-1] in [u'章', u'节']:
                    self.font_size = top_size[phrase[-1]]  # 将 章 节 的字号 统一到一个较大值
                    phrase = phrase[1:-1]

            if phrase is not '':
                is_subtitle = True
                for c in phrase:
                    if c not in base_word:
                        is_subtitle = False
                self.set_subtitle(is_subtitle)
                if is_subtitle:
                    self.subtitle_id = text_unicode.split(separator)[0]
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
        self.major_min_indent = min_indent
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
                    if u'（三）' in ele.text:
                        print __file__, sys._getframe().f_lineno
                    if ele.is_new_para(self.major_min_indent, self.max_chars_in_a_line, self.elements[i-1]):
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

class Doc(object):

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
                    if para.is_subtitle:
                        self.raw_subtitles.append(para)

    def max_i_key(self, i, d):
        if len(d) > i:
            return sorted(d.keys(),reverse=True)[i]
        else:
            return []


    def extract_subtitle(self):
        self.collect_possible_subtitle()
        # 合并第几章节，肯定是
        fonts = {}
        max_font_size = 12
        for i, para in enumerate(self.raw_subtitles):
            if para.subtitle_id == u'一':
                max_font_size = max(max_font_size, para.font_size)
                break

        for i,para in enumerate(self.raw_subtitles):
            if u'第' not in para.subtitle_id:
                para.font_size = min(max_font_size,para.font_size) # 一、 一 这种类型的 最大不超过 第一个一
            print i, para.font_name, para.left, para.font_size, para.text
            if para.font_size not in fonts:
                fonts[para.font_size] = []
            fonts[para.font_size].append(i)
        top_raw_id = []
        if len(fonts) > 0 : # 至少存在一个 subtitle
            for raw_id in fonts[self.max_i_key(0, fonts)]:
                sub = {}
                sub['stName'] = self.raw_subtitles[raw_id].text
                sub['anchorId'] = self.raw_subtitles[raw_id].anchor_id()
                sub['sub'] = []
                self.subtitles.append(sub)
                top_raw_id.append(raw_id)

        if len(fonts) > 1: # 存在二级标题
            # 选出处在 一级标题内部，最多的标题
            fonts.pop(self.max_i_key(0, fonts))
            l,key = 0,0
            for k in fonts:  # 找出最长的列表
                if len(fonts[k]) > l:
                    l = max(l, len(fonts[k]))
                    key = k

            top_raw_id.append(len(self.raw_subtitles)) #方便处理最后一个
            for i in range(0,len(top_raw_id)-1):
                for raw_id in range(top_raw_id[i]+1, top_raw_id[i+1]):
                    if raw_id in fonts[key]: # 需要被拆分到一级标题中去
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

