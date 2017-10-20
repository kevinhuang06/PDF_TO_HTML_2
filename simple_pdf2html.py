#coding=utf-8

import re
import copy
import json

from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import *


from pdf2html import PDF2HTML
from table import TableFrame

from tools import *
#from visual import *
from page import Line
from page import Page
from page import Doc

UCC = 0

base_struct = {
    "Pages": [],
    "SubTitles": []
}

class simplePDF2HTML(PDF2HTML):

    # 转换格式主函数
    def convert(self, bias_param=None):
        if bias_param:
            self.bias_param = bias_param
        print "initializing the parser setting..."
        try:
            self.simpleParse()
        except Exception,ex:
            self.logger.log(0, self.pdf_path, ex)
            print ex
            self.success = False
            return


        try:
            self.parse_to_doc()
        except Exception,ex:
            self.logger.log(2, self.pdf_path, '{0}\t{1}'.format(self.ex_page_no, ex))
            self.success = False
        print "HTML file:{0}".format(self.html_path)
        with open(self.json_path, 'w') as f:
            f.write(self.doc.dumps_to_json())
        with open(self.html_path, 'w') as f:
            f.write(self.doc.dumps_to_html())
        if self.success:
            self.logger.log(3, self.pdf_path)

    def simpleParse(self):
        # 创建一个PDF文档解析器对象
        self.parser = PDFParser(self.reader)
        # 创建一个PDF文档对象存储文档结构
        self.document = PDFDocument(self.parser, self.password)
        # 检查文件是否允许文本提取
        if not self.document.is_extractable:
            raise PDFTextExtractionNotAllowed

        self.outline_levels = []
        self.outlines_dict = {}
        self.outline_titles = []
        self.drawn_outline = []
        self.outline_ids = []

        # 创建一个PDF资源管理器对象来存储共享资源
        self.rsrcmgr = PDFResourceManager()
        # 创建一个PDF设备对象
        self.laparams = LAParams()
        # 创建一个PDF页面聚合对象
        self.device = PDFPageAggregator(self.rsrcmgr, laparams=self.laparams)
        # 创建一个PDF解析器对象
        self.interpreter = PDFPageInterpreter(self.rsrcmgr, self.device)
        # 字符转换规则
        self.replace = re.compile(r'\s+')


    def empty_page(self, layout):
        text_box_cc = 0
        page_area = layout.width * layout.height
        sum_area = 0
        for x in layout:

            if text_box_cc is 0 and isinstance(x, LTTextBoxHorizontal):
                for c in x.get_text():
                    if c > u'一' and c < u'龥': #中文字范围
                        text_box_cc += 1
                        break
            if isinstance(x, LTFigure): # 单个Figure占比过大
                if (x.width * x.height) / page_area > 0.1:
                    sum_area += x.width * x.height
            #print sum_area/page_area
            if sum_area/page_area > 0.8: # 大面积被图片覆盖
                return True
        if text_box_cc is 0:  #页面中至少有一个汉字
            return True
        return False


    def parse_to_doc(self):
        # 循环遍历列表，每次处理一个page的内容
        page_idx = 1
        prev_text = None
        prev_size = None
        prev_weight = None
        prev_indent = None
        prev_align = None

        self.doc = Doc()
        for idx, miner_page in enumerate(PDFPage.create_pages(self.document)):
            page_idx = idx + 1
            self.ex_page_no = idx + 1
            print 'processing page: %s'%idx
            self.interpreter.process_page(miner_page)
            # 接受该页面的LTPage对象
            layout = self.device.get_result()

            if self.empty_page(layout):
                self.logger.log(1, self.pdf_path, page_idx)
                self.success = False
                return False

            page_lines,text_cols = parse_page_to_lines(layout)
            col_lines = []
            # 页面左右上下
            page_xrange = (layout.x0, layout.x1)

            content_xrange, indent_list, fontsize_list = self.get_indent_info(layout, page_xrange)
            if len(indent_list) == 0 or len(fontsize_list) == 0:  # 空白页
                continue
            major_indents, map_indents, major_size = self.get_conclude(indent_list, fontsize_list)
            typical_length = (content_xrange[1] - content_xrange[0]) / major_size
            # get table contents in advance
            #计算table
            table_points_list, bias, table_divider_list = self.get_tables(layout,text_cols)
            table_frames, table_drawn = self.gene_table_frames(table_points_list, bias, table_divider_list)
            # 去除嵌套结构以及页码的外框
            self.remove_redundant_struct(table_frames, table_drawn)
            # 将属于表格内的内容填进表格内
            in_table = []  # true / false
            self.add_text_to_tables(table_frames, layout, in_table)
            # 更新in_table
            self.update_intable(in_table, table_frames)

            # 写入表格内容以外的其他内容
            page = self.dumps_text(idx, layout, in_table, table_drawn, table_frames, page_xrange, map_indents,\
                                major_indents, typical_length, page_idx, content_xrange, major_size)
            self.doc.add(page)
        self.doc.extract_subtitle()



    def gene_table_frames(self, table_points_list, bias, table_divider_list):
        table_frames = []
        table_drawn = []  # true / false
        for i in range(len(table_points_list)):
            tmp_frame = TableFrame(table_points_list[i], bias, table_divider_list[i])
            if tmp_frame.grids:
                table_frames.append(tmp_frame)
                table_drawn.append(False)
        return table_frames, table_drawn

    def dumps_to_json(self):
        with open(self.json_path,'w') as f:
            base_struct['Pages'] = self.pages
            base_struct['SubTitles'] = self.subtitles
            print >>f,json.dumps(base_struct, ensure_ascii=False)

    def dumps_text(self, number,layout, in_table, table_drawn, table_frames, page_xrange, map_indents,\
                                major_indents, typical_length, page_idx, content_xrange, major_size):
        #page.append(Line(prev_text, prev_align, fontname, prev_size, prev_indent))
        x_idx = -1
        prev_text = None
        page = Page(number, typical_length, min(major_indents), page_xrange)
        fontname = None
        for x in layout:
            if (isinstance(x, LTTextBoxHorizontal)):  # if(isinstance(x, LTTextLineHorizontal)):
                # print re.sub(self.replace,'',x.get_text())
                x_idx += 1
                if in_table[x_idx] != -1:
                    if not table_drawn[in_table[x_idx]]: # 保证 table

                        page.add(table_frames[in_table[x_idx]])
                        table_drawn[in_table[x_idx]] = True
                    continue
                text = x.get_text()
                fontname, fontsize, location, line_width = self.get_font(x)

                actual_left = map_indents[location[0]]
                indent = self.get_indent(actual_left, major_indents)
                align = self.get_align(content_xrange, location, line_width, fontsize, major_size, debug=text)
                if fontsize == 0:
                    fontsize = 12
                length = line_width / fontsize
                # print text
                # raw_input()

                page.add(Line(text, align, fontname, fontsize, indent,length, [actual_left, x.y0]))  #增加到page中

        page.merge_lines_to_paragraph()
        return page
        #page.dumps_to_html()


    def update_intable(self, in_table, table_frames):
        for i in range(len(table_frames)):
            max_col = 1
            for line in table_frames[i].data:
                if len(line) > max_col:
                    max_col = len(line)
            if max_col <= 1:
                # not a real table, dirty data
                for j in range(len(in_table)):
                    if in_table[j] == i:
                        in_table[j] = -1

    def add_text_to_tables(self, table_frames, layout, in_table):
        # 将属于表格内的内容填进表格内
        for x in layout:
            if (isinstance(x, LTTextBoxHorizontal)):
                # in_table.append(-1) # -1 for not included in any table; else: the table frame's index
                table_idx = -1
                for line in x:
                    if (isinstance(line, LTTextLineHorizontal)):
                        for i in range(len(table_frames)):
                            # table_frames[i]
                            text_line = line.get_text()
                            corner1, corner2, empty = get_corners(line, False)

                            if table_frames[i].is_in_range(corner1) and table_frames[i].is_in_range(corner2):
                                table_idx = i
                                break
                        if table_idx != -1: #只处理第一box的第一项
                            break
                in_table.append(table_idx)
                # print "#%s"%table_idx
                if table_idx != -1:
                    for line in x:
                        if (isinstance(line, LTTextLineHorizontal)):
                            # table_frames[table_idx]
                            parts = {}  # location: text
                            for char in line:
                                if isinstance(char, LTChar):
                                    text_c = re.sub(self.replace, '', char.get_text())
                                    if len(text_c):
                                        corner1 = (char.x0, char.y1)
                                        corner2 = (char.x1, char.y0)
                                        location = table_frames[table_idx].locate(corner2)
                                        if (location):
                                            if location in parts.keys():
                                                parts[location] += text_c
                                            else:
                                                parts[location] = text_c
                            for location in parts.keys():
                                table_frames[table_idx].add_data(location, parts[location])
                                if table_frames[table_idx].font[location[0]][location[1]] == None:
                                    table_frames[table_idx].font[location[0]][location[1]] = int(line.y1 - line.y0)

    # 去除嵌套结构以及页码的外框
    def remove_redundant_struct(self, table_frames, table_drawn):
        i = len(table_frames) - 1
        while i > 0:
            j = i - 1
            while j >= 0:
                # print table_frames[i].grids
                # print table_frames[j].grids
                # print table_frames[i].included_in_table(table_frames[j])
                # print table_frames[j].included_in_table(table_frames[i])
                if table_frames[i].included_in_table(table_frames[j]):
                    table_frames.pop(j)
                    table_drawn.pop(j)
                    break
                elif table_frames[j].included_in_table(table_frames[i]):
                    table_frames.pop(i)
                    table_drawn.pop(i)
                    break
                j -= 1
            i -= 1

    def get_font(self, x):
        default_fontname = self.chinese_str('ABCDEE+宋体')
        for line in x:
            line_width = line.width
            line_height = round(line.height)
            location = (round(line.x0), round(line.x1))
            # print line # LTTextLineHorizontal
            for char in line:
                if isinstance(char, LTAnno):
                    continue
                else:
                    location = (round(char.x0), round(line.x1))
                    fontsize = round(char.size)
                    fontname = char.fontname.decode('gbk').encode('utf-8')  # ABCDEE-黑体 即加粗 ABCDEE-宋体 即不加粗
                    #print fontname, char.get_text(), fontsize
                    c = char.get_text()
                    if c > u'一' and c < u'龥':  # 中文字范围
                        return fontname, fontsize, location, line_width
            return default_fontname, line_height, location, line_width

    def get_indent(self, actual_left, major_indents):
        level_indent = max(major_indents[0], major_indents[1])
        if actual_left == level_indent:
            return 2.0
        else:
            return 0.0

    def get_indent_info(self, layout, page_xrange):
        most_left = page_xrange[1]
        most_right = page_xrange[0]
        indent_list = {}
        fontsize_list = {}

        for x in layout:
            if (isinstance(x, LTTextBoxHorizontal)):
                fontname, fontsize, location, line_width = self.get_font(x)
                if location[0] < most_left:
                    most_left = location[0]
                if location[1] > most_right:
                    most_right = location[1]
                if fontsize in fontsize_list.keys():
                    fontsize_list[fontsize] += 1
                else:
                    fontsize_list[fontsize] = 1
                indent = location[0]
                if indent in indent_list.keys():
                    indent_list[indent] += 1
                else:
                    indent_list[indent] = 1
            #elif (isinstance(x, LTFigure)):
        return (most_left, most_right), indent_list, fontsize_list

    def if_close_to(self, src, dst, mode='percent', threshold=0.1):
        if mode == 'percent':
            if (src >= dst * (1 - threshold)) and (src <= dst * (1 + threshold)):
                return True
            return False
        elif mode == 'absolute':
            if (src >= dst - threshold) and (src <= dst + threshold):
                return True
            return False

    def get_conclude(self, indent_list, fontsize_list):
        sorted_indents = self.sort_dict_by_val(indent_list)
        sorted_sizes = self.sort_dict_by_val(fontsize_list)
        mapping_list = {}
        for key in indent_list.keys():
            mapping_list[key] = key
        max_amount_indent = sorted_indents[0][0]
        max_amount_indent_2 = -1
        for item in sorted_indents[1:]:
            if self.if_close_to(item[0], max_amount_indent):
                mapping_list[item[0]] = max_amount_indent
            else:
                if max_amount_indent_2 == -1:  # 尚未决定第二缩进
                    max_amount_indent_2 = item[0]
                else:
                    if self.if_close_to(item[0], max_amount_indent_2):
                        mapping_list[item[0]] = max_amount_indent_2
                    else:
                        break
        max_amount_size = sorted_sizes[0][0]
        return (max_amount_indent, max_amount_indent_2), mapping_list, max_amount_size

    def get_align(self, content_xrange, location, line_width, fontsize, major_size, debug=None):
        threshold = 0.8
        ratio_lim = 0.67
        width_lim = 0.7
        size_threshold = 1.2
        percentage = line_width / (content_xrange[1] - content_xrange[0])
        delta_left = location[0] - content_xrange[0]
        delta_right = content_xrange[1] - location[1]
        delta1 = max(delta_left, delta_right)
        delta2 = min(delta_left, delta_right)
        ratio = None
        if delta1 != 0:
            ratio = delta2 / delta1
        else:  # delta2 <= delta1 = 0
            return "left"
        if ratio >= ratio_lim and (percentage < threshold or fontsize > major_size * size_threshold):
            return "center"
        if ratio < ratio_lim and percentage < width_lim:
            if delta_left < delta_right:
                return "left"
            else:
                return "right"
        return "left"

    def if_para_end(self, actual_left, major_indents, ratio):
        threshold = 0.7
        min_indent = min(major_indents[0], major_indents[1])
        if actual_left == min_indent:
            # 除非此行比较短，否则认定为没有分段
            if ratio < threshold:
                return True  #顶到最有边，句子字符数，不及最多字符数的70%
            return False #顶到最有边，句子字符数，多于最多字符数的70% （近似认为句子顶到最右边）
        else:
            return True

    def is_line(self, rect_elem):
        threshold = 3  # 2
        x_diff = rect_elem.x1 - rect_elem.x0
        y_diff = rect_elem.y1 - rect_elem.y0
        if x_diff < threshold:
            if y_diff > 3 * threshold:
                return "y"
            else:
                return "point"
        if y_diff < threshold:
            if x_diff > 3 * threshold:
                return "x"
            else:
                return "point"
        return False


    def get_closest_idx(self, goal_value, lst, threshold):
        closest_idx = -1
        for i in range(len(lst)):
            item = lst[i]
            if abs(item - goal_value) <= threshold:
                closest_idx = i
                break
        return closest_idx

    def split_table(self, y_and_sx):
        my_tables = []
        if len(y_and_sx) < 1:
            return [],[]
        sorted_lines = y_and_sx
        last_line = sorted_lines[0]
        my_tables = [[last_line]]
        for i in range(1, len(sorted_lines)):
            # 分段数相同，位置完全相等

            same_table = False

            # if len(last_line[1]) == len(sorted_lines[i][1]):
            #     same_table = True
            #     for k in range(len(last_line)-1, 0, -1):
            #         if not same(last_line[1][k], sorted_lines[i][1][k]):
            #             same_table = False
            #             break
            # 短线点集是长线点集子集的，合并
            if len(last_line[1]) >= len(sorted_lines[i][1]):
                same_table = is_sub_list(last_line[1], sorted_lines[i][1])
            else:
                same_table = is_sub_list(sorted_lines[i][1], last_line[1])

            if same_table:
                my_tables[-1].append(sorted_lines[i])
            else:
                my_tables.append([sorted_lines[i]])
            last_line = sorted_lines[i]

        single_table_id = []
        # 把单一线 添加到临近的表格上去，
        # 向下合并，单线一定要给到，点数比自己多的上边去，不然表格不封闭
        for idx, t in enumerate(my_tables):
            if len(t) == 1:
                single_table_id.append(idx)
        # 单一线和其他数据的分段数不同，若是在表头处，需要添加一条水平直线，对表头做切割。

        merge_pair = []
        for idx in single_table_id:
            prex_line = []
            next_line = []
            if idx > 0:
                prex_line = my_tables[idx - 1][-1][1]
            if idx + 1 < len(my_tables):
                next_line = my_tables[idx + 1][0][1]
            same_prex = 0
            same_next = 0
            for p in my_tables[idx][0][1]:
                for p_prex in prex_line:
                    if same(p, p_prex):
                        same_prex += 1
                for p_next in next_line:
                    if same(p, p_next):
                        same_next += 1
            # 优先做表头的线
            if same_next > same_prex:
                if same_next > 1:
                    merge_pair.append((idx, idx + 1))
            else:
                if same_prex > 1:  # 控制合并时的 相似点数量
                    if (idx - 1, idx) not in merge_pair:
                        merge_pair.append((idx, idx - 1))

        skip_segs = {}
        # 反向遍历列表,

        for pair in merge_pair[::-1]:
            for l in my_tables[pair[0]]:
                # print l
                # 0 是下边的table, 1 是上边的table
                if pair[0] < pair[1]:
                    my_tables[pair[1]].insert(0, l)
                else:
                    top_line = my_tables[pair[1]][-1]
                    # 向下合并，当表头
                    # 说明表头存在单元格合并，需要增加水平线
                    if len(top_line[1]) > len(l[1]):
                        ave_y = (top_line[0] + l[0]) / 2
                        skip_segs[ave_y] = 0
                        # split_l = (ave_y, top_line[1])
                        # my_tables[pair[1]].append(split_l)
                        # add_segs(top_line[1][1:], ave_y, table_outline_elem_lst)
                    my_tables[pair[1]].append(l)
            del my_tables[pair[0]]
            # print len(my_tables)

            # 保证 表尾的分段数量部大于表头
        for idx in range(len(my_tables) - 1, 0, -1):
            my_tables[idx].sort()
            t = my_tables[idx]
            if len(t[-1][1]) > len(t[0][1]):  # 表头大于表尾，考虑与下一个表格合并
                if len(t[-1][1]) == len(my_tables[idx - 1][1][-1]):  # 表头和下方表头 相同，考虑合并
                    for l in t:
                        my_tables[idx - 1].append(l)
                    del my_tables[idx]
        # 对短直线做修正,至少和表尾相同
        for idx, t in enumerate(my_tables):
            for l_id, line in enumerate(t):
                if len(line[1]) < len(t[0][1]) and l_id < len(t) - 1:  # 表头不参与
                    my_tables[idx][l_id] = (line[0], t[0][1])

        return my_tables,skip_segs
    #################
    # steps in get_tables
    # step 1
    def get_tables_elements(self, layout, text_cols):
        max_stroke = -1
        table_outline_elem_lst = []  # contents: {'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1, 'isLine': isLine}
        table_raw_dash_lst = []
        dashline_parser_xs = []
        dashline_parser_ys = []
        slash_elem_lst = {}
        y_and_its_xs = {}
        num_horizon_line = 0
        num_vertical_line = 0


        for x in layout:
            # if(isinstance(x, LTRect)):

            if isinstance(x, LTRect) or isinstance(x, LTFigure):
                left = x.x0
                right = x.x1
                top = x.y1
                bottom = x.y0
                left = int(left)
                right = int(right)
                top = int(top)
                bottom = int(bottom)
                isLine = self.is_line(x)
                """
                if isinstance(x,LTLine):
                    if isLine == 'x':
                        top -= 1
                        bottom += 1
                    else:
                        left -= 1
                        right += 1
                """
                if isLine:  # a line
                    # fetch data
                    if isLine == 'x':
                        num_horizon_line += 1
                        line_stroke = top - bottom
                        shared_y = (top + bottom) / 2.0
                        if shared_y not in dashline_parser_ys:
                            dashline_parser_ys.append(shared_y)
                        if left not in dashline_parser_xs:
                            dashline_parser_xs.append(left)
                        if right not in dashline_parser_xs:
                            dashline_parser_xs.append(right)
                        flag = True
                        for k in y_and_its_xs:
                            if same(shared_y, k):
                                y_and_its_xs[k].add(left)
                                y_and_its_xs[k].add(right)
                                flag = False
                                break
                        if flag:
                            y_and_its_xs[shared_y] = set()  # 去重相近的重复线
                            y_and_its_xs[shared_y].add(left)
                            y_and_its_xs[shared_y].add(right)
                    elif isLine == 'y':
                        num_vertical_line +=1
                        line_stroke = right - left
                        shared_x = (left + right) / 2.0
                        if shared_x not in dashline_parser_xs:
                            dashline_parser_xs.append(shared_x)
                        if top not in dashline_parser_ys:
                            dashline_parser_ys.append(top)
                        if bottom not in dashline_parser_ys:
                            dashline_parser_ys.append(bottom)
                    elif isLine == 'point':
                        line_stroke = min(top - bottom, right - left)  # max?
                    # update data
                    if line_stroke > max_stroke:
                        max_stroke = line_stroke
                if isLine:
                    tmp_elem = {
                        'x0': left,
                        'x1': right,
                        'y0': bottom,
                        'y1': top,
                        'isLine': isLine
                    }
                    if isLine == 'point':
                        table_raw_dash_lst.append(tmp_elem)
                    elif isLine == 'y':
                        pass
                        #tmp_elem['x1'] = tmp_elem['x0']
                        slash_elem_lst[(bottom,top)] = 0
                        #table_outline_elem_lst.append(tmp_elem)
                         # if  tmp_elem['x1'] == tmp_elem['x0']:
                         #     table_outline_elem_lst.append(tmp_elem)
                         # else:
                         #     tmp_elem['x1'] = tmp_elem['x0']
                         #     slash_elem_lst.append(tmp_elem)



        #remove y-line that is too close
        #remove_y_id = []
        #for p in table_outline_elem_lst:

        #remove point that is too close
        for k in y_and_its_xs:

            a = sorted(list(y_and_its_xs[k]))
            last_p = a[0]
            remove_id = []
            if len(a) > 10:
                pass
            for i in range(1,len(a)):
                if same(last_p, a[i]):
                    if i == 1: #最左对，移除靠右
                        remove_id.insert(0, 1)
                    else:
                        remove_id.insert(0, i-1)
                        last_p = a[i]
                else:
                    last_p = a[i]
            for idx in remove_id:
                del a[idx]

            y_and_its_xs[k] = a
        y_and_sx = sorted(y_and_its_xs.iteritems(), key=lambda x: x[0])

        #移除页眉线和页脚线
        if y_and_sx is not None and len(y_and_sx) > 1:
            if len(y_and_sx[0][1]) == 2:
                del y_and_sx[0]
            if len(y_and_sx[-1][1]) == 2:
                del y_and_sx[-1]

        # 删除过短的线段
        for idx, l in enumerate(y_and_sx):
            last_p = l[1][0]
            pairs = []
            for i in range(1, len(l[1])):
                if abs(last_p - l[1][i]) <= 15:  # 12 is the size of a char
                    pairs.insert(0, [i - 1, i])
                last_p = l[1][i]
            for prex, curr in pairs:
                if prex == 0:
                    del y_and_sx[idx][1][curr]  # 如果是最左边，删除靠右的
                else:
                    del y_and_sx[idx][1][prex]
            y_and_sx[idx][1].sort()
            # add_segs(l[1],l[0],table_outline_elem_lst)

        #利用文本补全 最上和最下的表格线
        uu = []
        for l in text_cols:
            uu.append([l['box'][0][1], l['box'][1][1], len(l['text_lines'])])
        uu.sort(key=lambda x: x[0])
        if len(uu) > 0 and len(y_and_sx) > 1:
            bot_line = y_and_sx[0]
            top_line = y_and_sx[-1]
            for text_line in uu:
                if text_line[0] < bot_line[0]:
                    #text_line[2]表示的是矩形的个数
                    if len(bot_line[1]) == text_line[2] + 1: # 左下角
                        y_and_sx.insert(0, [text_line[0],bot_line[1]])
                        break
                else:
                    break
            for text_line in uu[::-1]:
                if text_line[1] > top_line[0]:
                    if len(top_line[1]) == text_line[2] + 1: # 右上角
                        y_and_sx.append([text_line[1], top_line[1]])
                        break
                else:
                    break
            #pass


        # split_tables
        my_tables = []
        if  num_horizon_line > 2 and num_vertical_line < 2:
            my_tables, skip_segs = self.split_table(y_and_sx)
            for idx,t in enumerate(my_tables):
                #找到 最大y,最小y 切分数据
                t.sort(key=lambda x: x[0], reverse=True)  #从表头向表尾
                up = t[0][0] #top y
                bottom = t[-1][0]
                ys = []
                last_y = 0
                text_box = []
                for l in text_cols:
                    if in_range(l['box'][0][1], bottom, up) and in_range(l['box'][1][1], bottom, up) :
                        text_box.append([l['box'][0][1],l['box'][1][1]])
                text_box.sort(key= lambda x:x[0])
                if len(text_box) == 0:
                    continue
                last_box = text_box[0]
                show_up = False
                for i in range(1,len(text_box)):
                    y = (last_box[1] + text_box[i][0])/2
                    last_box = text_box[i]
                    ys.append(y)
                    my_tables[idx].append((y,t[-1][1],'text'))
                    #增加横线
                    #add_segs(t[-1][1], y, table_outline_elem_lst)

            for i in range(len(my_tables)):
                my_tables[i].sort(key=lambda x:x[0])
                merge_ys(my_tables[i])
                uniform_segs(my_tables[i])

                for l in my_tables[i]:
                    if l[0] not in skip_segs:
                        add_segs(l[1], l[0], table_outline_elem_lst)
                # 表头分割 单独画
                split_l = sheet_head_split(my_tables[i])
                if split_l:
                    start = split_l[2]
                    add_segs(split_l[1][start:], split_l[0], table_outline_elem_lst)
                    my_tables[i].append(split_l)

            for t in my_tables:
                t.sort(key=lambda x: x[0])
                for i in range(1, len(t)):
                    last_line = t[i - 1]
                    for j in range(len(last_line[1])):

                        x = last_line[1][j]
                        tmp_elem = {
                            'x0': x,
                            'x1': x,
                            'y0': last_line[0],
                            'y1': t[i][0],
                            'isLine': 'y'
                        }
                        table_outline_elem_lst.append(tmp_elem)
        else:

            # 移除距离太近的y
            if len(y_and_sx) > 0:
                del_ids = []
                last_l = y_and_sx[0]
                for i in range(1, len(y_and_sx)):
                    if abs(last_l[0] - y_and_sx[i][0]) < 8: # 距离太近
                        # 同列数，优先保留下边线，防止线都被移除了
                        if len(y_and_sx[i][1]) <= len(last_l[1]):
                            del_ids.insert(0, i)
                        else:
                            del_ids.insert(0, i-1)
                            last_l = y_and_sx[i]
                    else:
                        last_l = y_and_sx[i]
                for idx in del_ids:
                    del y_and_sx[idx]

            #用竖线进行表格分割，先求竖线分段
            segs = split_lines(slash_elem_lst)
            my_tables= []
            for s in segs:
                t = []
                for l in y_and_sx:
                    if l[0] > s[0]-12 and l[0]<s[1]+12:
                        t.append(l)
                if len(t) > 0:
                    my_tables.append(t)


            #补全短直线 && 保证两侧对齐
            for i,t in enumerate(my_tables):
                left = 1000
                right = 0
                for l in t:
                    left = min(l[1][0], left)
                    right = max(l[1][-1], right)
                #保证表格封闭
                for j,l in enumerate(my_tables[i]):
                    li = l[1]
                    if not same(l[1][0],left):
                        li.insert(0, left)
                    if not same(l[1][-1], right):
                        li.append(right)
                    my_tables[i][j] = (l[0], li)

                for j in range(1,len(my_tables[i])-1):
                    if len(my_tables[i][j][1]) < len(my_tables[i][j-1][1]):
                        my_tables[i][j]=(my_tables[i][j][0],my_tables[i][j-1][1])



            #画横线
            for l in y_and_sx:
                add_segs(l[1], l[0], table_outline_elem_lst)
            #画竖线
            for t in my_tables:
                t.sort(key=lambda x: x[0])
                for i in range(1, len(t)):
                    last_line = t[i - 1]
                    for j in range(len(last_line[1])):
                        x = last_line[1][j]
                        tmp_elem = {
                            'x0': x,
                            'x1': x,
                            'y0': last_line[0],
                            'y1': t[i][0],
                            'isLine': 'y'
                        }
                        table_outline_elem_lst.append(tmp_elem)

        lines = []
        points = {}
        for x in layout:
            if isinstance(x, LTLine):
                left = x.x0
                right = x.x1
                top = x.y1
                bottom = x.y0
                # if same(x.x0, x.x1) or same(x.y0, x.y1): # 是dot
                #    continue
                flag = True

                for t in my_tables:
                    if in_range(x.y0, t[0][0], t[-1][0]) or in_range(x.y1, t[0][0], t[-1][0]):
                        flag = False
                        break
                if flag:
                    lines.append([(x.x0, x.y0), (x.x1, x.y1)])
                #else:
                #    pass
        # lines = merge_same_line(raw_lines)

        for seg in self.add_cross_point(lines, points):
            direct = 'x'
            if seg[0][0] == seg[1][0]:  # vertical
                direct = 'y'
            tmp_elem = {
                'x0': seg[0][0],
                'y0': seg[0][1],
                'x1': seg[1][0],
                'y1': seg[1][1],
                'isLine': direct
            }
            table_outline_elem_lst.append(tmp_elem)



        #raw_lines = []


        #print len(table_raw_dash_lst),len(table_outline_elem_lst)

    ###

        if max_stroke >= 0:
            bias = self.bias_param[0] * max_stroke  # 3 # 2 # 1.5
        else:
            bias = self.bias_param[1]  # 5 # 3 # 2

        return bias, table_outline_elem_lst, table_raw_dash_lst, dashline_parser_xs, dashline_parser_ys

    # aid function
    def line_merge(self, range1, range2, bias=0):
        assert len(range1) == 2 and len(range2) == 2, "range should be an array containing 2 elements"
        try:
            r1_min = min(range1) - bias
            r1_max = max(range1) + bias
            r2_min = min(range2) - bias
            r2_max = max(range2) + bias
        except Exception,ex:
            pass
        if (r1_min - r2_min) * (r1_min - r2_max) <= 0 or (r1_max - r2_min) * (r1_max - r2_max) <= 0 \
                or (r2_min - r1_min) * (r2_min - r1_max) <= 0 or (r2_max - r1_min) * (r2_max - r1_max) <= 0:
            merged_range = [[min(r1_min, r2_min) + bias, max(r1_max, r2_max) - bias]]
        else:
            merged_range = [range1, range2]
        return merged_range

    # step 2
    def get_tables_dashlines(self, table_raw_dash_lst, bias):
        # 处理一下 table_outline_elem_lst
        # 首先把虚线找出来连起来
        raw_dashline_dot_xs = {}  # (x1, x2): [idx1, idx2, ...]
        raw_dashline_dot_ys = {}  # (y1, y2): [idx1, idx2, ...]
        for i in range(len(table_raw_dash_lst)):
            raw_dashline_dots = table_raw_dash_lst[i]
            left = raw_dashline_dots['x0']
            right = raw_dashline_dots['x1']
            top = raw_dashline_dots['y1']
            bottom = raw_dashline_dots['y0']
            # draw.square(left, right, top, bottom)
            dot_x_key = (left, right)
            dot_y_key = (bottom, top)
            if dot_x_key in raw_dashline_dot_xs.keys():
                raw_dashline_dot_xs[dot_x_key].append([bottom, top])
            else:
                raw_dashline_dot_xs[dot_x_key] = [[bottom, top]]
            if dot_y_key in raw_dashline_dot_ys.keys():
                raw_dashline_dot_ys[dot_y_key].append([left, right])
            else:
                raw_dashline_dot_ys[dot_y_key] = [[left, right]]
        # lines merged
        table_dashlines = []  # contents: element
        for dot_x_key in raw_dashline_dot_xs.keys():  # vertical lines
            # 针对每一个 x 线段，找这个坐标上能连起来的y线段；因为预先排序，所以只需要看前一个就行
            candidate_ys = raw_dashline_dot_xs[dot_x_key]
            candidate_ys.sort()
            first_line = [candidate_ys[0][0], candidate_ys[0][1]]
            lines_y_list = [first_line]
            for dot_y in candidate_ys[1:]:
                last_y_idx = len(lines_y_list) - 1
                last_line = lines_y_list[last_y_idx]
                # print line_merge(last_line, dot_y, bias=bias)
                merged_result = self.line_merge(last_line, dot_y, bias=bias)
                if len(merged_result) == 1:
                    # successfully merged
                    lines_y_list[last_y_idx][0] = merged_result[0][0]
                    lines_y_list[last_y_idx][1] = merged_result[0][1]
                else:
                    lines_y_list.append([dot_y[0], dot_y[1]])
            # raw_input("******ended dot {0}*********".format(dot_x_key))
            left = min(dot_x_key[0], dot_x_key[1])
            right = max(dot_x_key[0], dot_x_key[1])
            for line_y in lines_y_list:
                bottom = min(line_y[1], line_y[0])
                top = max(line_y[1], line_y[0])

                if top - bottom > 2 * bias:
                    tmp_elem = {
                        'x0': left,
                        'x1': right,
                        'y0': bottom,
                        'y1': top,
                        'isLine': 'y'
                    }
                    table_dashlines.append(tmp_elem)

        for dot_y_key in raw_dashline_dot_ys.keys():
            # 对y同理
            candidate_xs = raw_dashline_dot_ys[dot_y_key]
            candidate_xs.sort()
            first_line = [candidate_xs[0][0], candidate_xs[0][1]]
            lines_x_list = [first_line]
            for dot_x in candidate_xs[1:]:
                last_x_idx = len(lines_x_list) - 1
                last_line = lines_x_list[last_x_idx]
                merged_result = self.line_merge(last_line, dot_x, bias=bias)
                if len(merged_result) == 1:
                    lines_x_list[last_x_idx][0] = merged_result[0][0]
                    lines_x_list[last_x_idx][1] = merged_result[0][1]
                else:
                    lines_x_list.append([dot_x[0], dot_x[1]])
            top = max(dot_y_key[0], dot_y_key[1])
            bottom = min(dot_y_key[0], dot_y_key[1])
            for line_x in lines_x_list:
                left = min(line_x[0], line_x[1])
                right = max(line_x[0], line_x[1])
                if right - left > 2 * bias:
                    tmp_elem = {
                        'x0': left,
                        'x1': right,
                        'y0': bottom,
                        'y1': top,
                        'isLine': 'x'
                    }
                    table_dashlines.append(tmp_elem)
        return table_dashlines

    # step 2.1: 合并dashline到其他表格边框元素列表之中
    def get_tables_elements_all(self, table_outline_elem_lst, table_dashlines, dashline_parser_xs, dashline_parser_ys):
        for dashline in table_dashlines:
            if dashline['isLine'] == 'x':
                # horizontal
                start_val = min(dashline['x0'], dashline['x1'])
                end_val = max(dashline['x0'], dashline['x1'])
                start_idx = -1
                end_idx = -1
                for i in range(len(dashline_parser_xs)):
                    if dashline_parser_xs[i] == start_val:
                        start_idx = i
                    if dashline_parser_xs[i] == end_val:
                        end_idx = i
                        break
                assert start_idx != -1 and end_idx != -1 and start_idx <= end_idx, "1# {0}, {1} not in {2}".format(
                    start_val, end_val, dashline_parser_xs)
                for i in range(start_idx, end_idx):
                    table_outline_elem_lst.append({
                        'x0': dashline_parser_xs[i],
                        'x1': dashline_parser_xs[i + 1],
                        'y0': dashline['y0'],
                        'y1': dashline['y1'],
                        'isLine': 'x'
                    })
            elif dashline['isLine'] == 'y':
                # horizontal
                start_val = min(dashline['y0'], dashline['y1'])
                end_val = max(dashline['y0'], dashline['y1'])
                start_idx = -1
                end_idx = -1
                for i in range(len(dashline_parser_ys)):
                    if dashline_parser_ys[i] == start_val:
                        start_idx = i
                    if dashline_parser_ys[i] == end_val:
                        end_idx = i
                        break
                assert start_idx != -1 and end_idx != -1 and start_idx <= end_idx, "2# {0}, {1} not in {2}".format(
                    start_val, end_val, dashline_parser_ys)
                for i in range(start_idx, end_idx):
                    table_outline_elem_lst.append({
                        'x0': dashline['x0'],
                        'x1': dashline['x1'],
                        'y0': dashline_parser_ys[i],
                        'y1': dashline_parser_ys[i + 1],
                        'isLine': 'y'
                    })
        return table_outline_elem_lst

    # step 3: 分出大致区域
    def get_tables_areas(self, table_outline_elem_lst, bias):
        # 粗略分出不同表格的子区域
        clean_tables_area = []  # 每个表占的x, y范围, 内容: [[x1, x2], [y1, y2]]

        for outline_elem in table_outline_elem_lst:
            tmp_x_range = [outline_elem['x0'], outline_elem['x1']]
            tmp_y_range = [outline_elem['y1'], outline_elem['y0']]
            i = len(clean_tables_area) - 1
            while i >= 0:
                new_x_range = self.line_merge(clean_tables_area[i][0], tmp_x_range, bias=bias)
                new_y_range = self.line_merge(clean_tables_area[i][1], tmp_y_range, bias=bias)

                if len(new_x_range) == 1 and len(new_y_range) == 1:
                    # successfully merged
                    tmp_x_range[0] = new_x_range[0][0]
                    tmp_x_range[1] = new_x_range[0][1]
                    tmp_y_range[0] = new_y_range[0][0]
                    tmp_y_range[1] = new_y_range[0][1]
                    clean_tables_area.pop(i)
                i -= 1
            clean_tables_area.append([tmp_x_range, tmp_y_range])
        clean_tables_lst = []  # grouped outline elements, contents: [elem1, elem2, ...]
        for elem in clean_tables_area:
            clean_tables_lst.append([])
        for outline_elem in table_outline_elem_lst:
            tmp_x_range = [outline_elem['x0'], outline_elem['x1']]
            tmp_y_range = [outline_elem['y1'], outline_elem['y0']]
            tmp_table_idx = -1
            for i in range(len(clean_tables_area)):
                new_x_range = self.line_merge(clean_tables_area[i][0], tmp_x_range, bias=bias)
                new_y_range = self.line_merge(clean_tables_area[i][1], tmp_y_range, bias=bias)
                if len(new_x_range) == 1 and len(new_y_range) == 1:
                    tmp_table_idx = i
                    break
            if tmp_table_idx >= 0:
                clean_tables_lst[tmp_table_idx].append(outline_elem.copy())
        return clean_tables_lst

    # step 4:
    def get_tables_raw_frame(self, clean_tables_lst, bias):
        raw_lines = []  # contents: ((x1, y1), (x2, y2))
        raw_points = {}  # contents: (x, y): [idx1, idx2, ...] - the index of corresponding lines
        points_visited = {}  # contents: (x, y) : True / False
        for clean_tables_lst_elem in clean_tables_lst:
            raw_points_x = []  # contents: x
            raw_points_y = []  # contents: y
            for outline_elem in clean_tables_lst_elem:
                left = outline_elem['x0']
                right = outline_elem['x1']
                top = outline_elem['y1']
                bottom = outline_elem['y0']
                idx_left = self.get_closest_idx(left, raw_points_x, bias)
                idx_right = self.get_closest_idx(right, raw_points_x, bias)
                idx_top = self.get_closest_idx(top, raw_points_y, bias)
                idx_bottom = self.get_closest_idx(bottom, raw_points_y, bias)
                if idx_left >= 0:
                    left = raw_points_x[idx_left]
                if idx_right >= 0:
                    right = raw_points_x[idx_right]
                if idx_top >= 0:
                    top = raw_points_y[idx_top]
                if idx_bottom >= 0:
                    bottom = raw_points_y[idx_bottom]

                isLine = outline_elem['isLine']
                if isLine:  # a line
                    # fetch data
                    if isLine == 'x':
                        if idx_left == -1:
                            raw_points_x.append(left)
                        idx_right = self.get_closest_idx(right, raw_points_x, bias)
                        if idx_right == -1:
                            raw_points_x.append(right)
                        fixed_y = (top + bottom) / 2.0
                        #fixed_y = int(fixed_y)
                        idx_fixed_y = self.get_closest_idx(fixed_y, raw_points_y, bias)
                        if idx_fixed_y >= 0:
                            fixed_y = raw_points_y[idx_fixed_y]
                        else:
                            raw_points_y.append(fixed_y)

                        pt1 = (left, fixed_y)
                        pt2 = (right, fixed_y)
                    elif isLine == 'y':
                        # print 'y'
                        if idx_top == -1:
                            raw_points_y.append(top)
                        idx_bottom = self.get_closest_idx(bottom, raw_points_y, bias)
                        if idx_bottom == -1:
                            raw_points_y.append(bottom)
                        fixed_x = (left + right) / 2.0
                        #fixed_x = int(fixed_x)
                        idx_fixed_x = self.get_closest_idx(fixed_x, raw_points_x, bias)
                        if idx_fixed_x >= 0:
                            fixed_x = raw_points_x[idx_fixed_x]
                        else:
                            raw_points_x.append(fixed_x)

                        pt1 = (fixed_x, top)
                        pt2 = (fixed_x, bottom)
                    # update data
                    if pt1 not in raw_points.keys():
                        raw_points[pt1] = []
                        points_visited[pt1] = False
                    if pt2 not in raw_points.keys():
                        raw_points[pt2] = []
                        points_visited[pt2] = False
                    tmp_idx_line = len(raw_lines)
                    if (pt1, pt2) not in raw_lines and (pt2, pt1) not in raw_lines:
                        raw_lines.append((pt1, pt2))
                        raw_points[pt1].append(tmp_idx_line)
                        raw_points[pt2].append(tmp_idx_line)
                else:  # a rectangle
                    if idx_left == -1:
                        raw_points_x.append(left)
                    idx_right = self.get_closest_idx(right, raw_points_x, bias)
                    if idx_right == -1:
                        raw_points_x.append(right)
                    if idx_top == -1:
                        raw_points_y.append(top)
                    idx_bottom = self.get_closest_idx(bottom, raw_points_y, bias)
                    if idx_bottom == -1:
                        raw_points_y.append(bottom)
                    pt1 = (left, top)
                    pt2 = (right, top)
                    pt3 = (right, bottom)
                    pt4 = (left, bottom)
                    points_visited[pt1] = False
                    points_visited[pt2] = False
                    points_visited[pt3] = False
                    points_visited[pt4] = False
                    if pt1 not in raw_points:
                        raw_points[pt1] = []
                    if pt2 not in raw_points:
                        raw_points[pt2] = []
                    if pt3 not in raw_points:
                        raw_points[pt3] = []
                    if pt4 not in raw_points:
                        raw_points[pt4] = []
                    # raw_lines.append( (pt1, pt2) )
                    tmp_idx_line = len(raw_lines)
                    if (pt1, pt2) not in raw_lines and (pt2, pt1) not in raw_lines:
                        raw_lines.append((pt1, pt2))
                        raw_points[pt1].append(tmp_idx_line)
                        raw_points[pt2].append(tmp_idx_line)
                    # raw_lines.append( (pt2, pt3) )
                    tmp_idx_line = len(raw_lines)
                    if (pt2, pt3) not in raw_lines and (pt3, pt2) not in raw_lines:
                        raw_lines.append((pt2, pt3))
                        raw_points[pt2].append(tmp_idx_line)
                        raw_points[pt3].append(tmp_idx_line)
                    # raw_lines.append( (pt3, pt4) )
                    tmp_idx_line = len(raw_lines)
                    if (pt3, pt4) not in raw_lines and (pt4, pt3) not in raw_lines:
                        raw_lines.append((pt3, pt4))
                        raw_points[pt3].append(tmp_idx_line)
                        raw_points[pt4].append(tmp_idx_line)
                    # raw_lines.append( (pt4, pt1) )
                    tmp_idx_line = len(raw_lines)
                    if (pt4, pt1) not in raw_lines and (pt1, pt4) not in raw_lines:
                        raw_lines.append((pt4, pt1))
                        raw_points[pt4].append(tmp_idx_line)
                        raw_points[pt1].append(tmp_idx_line)

        # calculate the points included in a table, and the grids
        assert len(points_visited.keys()) == len(raw_points.keys()), "points amount and points list length do not match"
        return raw_lines, raw_points, points_visited

    def get_tables_init_info(self, raw_points, raw_lines, points_visited):
        '''Grouped Points and Lines'''
        point_list = raw_points.copy()

        def recursively_get_group(tmp_point):
            ret_val = []
            # if the point has already been visited
            if not points_visited[tmp_point]:
                points_visited[tmp_point] = True
                ret_val.append(tmp_point)
                # get the neighbours
                next_idx_lst = point_list.pop(tmp_point)
                for idx in next_idx_lst:
                    line = raw_lines[idx]
                    next_point = line[0]
                    if next_point == tmp_point:
                        next_point = line[1]
                    if points_visited[next_point]:
                        continue
                    next_list = recursively_get_group(next_point)
                    ret_val.extend(next_list)

            return ret_val

        table_list = []  # points in tables
        table_line_list = []  # lines that belong to a specific table
        divider_list = []  # the lines
        while len(point_list.keys()):
            next_starting_point = point_list.keys()[0]
            next_group = recursively_get_group(next_starting_point)
            if len(next_group) > 2:  # it is a table, not a line
                next_group.sort()
                table_list.append(next_group)
                divider_list.append([])
                table_line_list.append([])

        # get the lines' list
        for line in raw_lines:
            for i in range(len(table_list)):
                if line[0] in table_list[i] or line[1] in table_list[i]:
                    table_line_list[i].append(line)
                    break

        return table_list, table_line_list, divider_list

    def get_tables_divider_list(self, table_list, table_line_list, divider_list, bias):
        # get the regularized lines
        for i in range(len(table_list)):
            tmp_xs = []
            tmp_ys = []
            tmp_table = table_list[i]
            tmp_lines = table_line_list[i]

            # print tmp_table
            for pt in tmp_table:
                pt_x = pt[0]
                pt_y = pt[1]
                if pt_x not in tmp_xs:
                    tmp_xs.append(pt_x)
                if pt_y not in tmp_ys:
                    tmp_ys.append(pt_y)
            tmp_xs.sort()
            tmp_ys.sort()

            # 规范一下xs和ys从而避免一个线段被分成两个的状况

            len_xs = len(tmp_xs)
            len_ys = len(tmp_ys)
            if len_xs < 2 or len_ys < 2:
                continue
            keep_xs = {}
            keep_ys = {}
            x_lines = {}  # x: [[y1, y2], [y1', y2']...], same x, vertical
            y_lines = {}  # y: [[x1, x2], [x1', x2']...], same y, horizontal
            keep_xs[tmp_xs[0]] = True
            keep_ys[tmp_ys[0]] = True
            keep_xs[tmp_xs[len_xs - 1]] = True
            keep_ys[tmp_ys[len_ys - 1]] = True

            for tmp_x in tmp_xs[1: len_xs - 1]:
                keep_xs[tmp_x] = False
            for tmp_y in tmp_ys[1: len_ys - 1]:
                keep_ys[tmp_y] = False

            for line in tmp_lines:
                # 找出合法的点
                pt1 = min(line[0], line[1])
                pt2 = max(line[0], line[1])
                if pt1[0] == pt2[0]:
                    tmp_x = pt1[0]
                    tmp_y = [pt1[1], pt2[1]]
                    keep_xs[tmp_x] = True
                    if tmp_x in x_lines.keys():
                        # merge
                        # prev_tmp_y = copy.copy(tmp_y)
                        n_tmp_col_lines = len(x_lines[tmp_x])
                        for c in range(n_tmp_col_lines):
                            tmp_idx = n_tmp_col_lines - 1 - c
                            merged_line = self.line_merge(x_lines[tmp_x][tmp_idx], tmp_y, bias=bias)
                            if len(merged_line) == 1:
                                x_lines[tmp_x].pop(tmp_idx)
                                tmp_y[0] = merged_line[0][0]
                                tmp_y[1] = merged_line[0][1]
                        x_lines[tmp_x].append(tmp_y)
                    else:
                        x_lines[tmp_x] = [tmp_y]
                elif pt1[1] == pt2[1]:

                    tmp_y = pt1[1]
                    tmp_x = [pt1[0], pt2[0]]
                    keep_ys[tmp_y] = True
                    if tmp_y in y_lines.keys():
                        # merge
                        n_tmp_row_lines = len(y_lines[tmp_y])
                        for r in range(n_tmp_row_lines):
                            tmp_idx = n_tmp_row_lines - 1 - r
                            merged_line = self.line_merge(y_lines[tmp_y][tmp_idx], tmp_x, bias=bias)
                            if len(merged_line) == 1:
                                y_lines[tmp_y].pop(tmp_idx)
                                tmp_x[0] = merged_line[0][0]
                                tmp_x[1] = merged_line[0][1]
                        y_lines[tmp_y].append(tmp_x)
                    else:
                        y_lines[tmp_y] = [tmp_x]
            tmp_xs = [k for k in keep_xs.keys() if keep_xs[k]]
            tmp_ys = [k for k in keep_ys.keys() if keep_ys[k]]
            tmp_xs.sort()
            tmp_ys.sort()
            # table list update!
            j = len(tmp_table) - 1
            while j >= 0:
                if tmp_table[j][0] not in tmp_xs or tmp_table[j][1] not in tmp_ys:
                    table_list[i].pop(j)
                j -= 1
            # line update
            tmp_lines = []

            for x_line_key in x_lines.keys():
                x_lines[x_line_key].sort()
                for x_line in x_lines[x_line_key]:
                    pt1 = (x_line_key, x_line[0])
                    pt2 = (x_line_key, x_line[1])
                    tmp_lines.append((pt1, pt2))
            for y_line_key in y_lines.keys():
                y_lines[y_line_key].sort()
                for y_line in y_lines[y_line_key]:
                    pt1 = (y_line[0], y_line_key)
                    pt2 = (y_line[1], y_line_key)
                    tmp_lines.append((pt1, pt2))
            # 处理分割线
            for line in tmp_lines:
                pt1 = min(line[0], line[1])
                pt2 = max(line[0], line[1])
                #if pt1[0] == pt2[0] and pt1[1] == pt2[1]:
                #    continue
                if pt1[0] == pt2[0]:  # same x
                    start_line_idx = -1
                    end_line_idx = -1

                    for idx in range(len(tmp_ys)):
                        if same(tmp_ys[idx], pt1[1]):
                            start_line_idx = idx
                        if same(tmp_ys[idx], pt2[1]):
                            end_line_idx = idx
                            break  # sorted
                    if start_line_idx == -1 or end_line_idx == -1:
                        pass
                    assert start_line_idx != -1 and end_line_idx != -1, "unrecorded point axis {0} or {1}, not recorded in {2}".format(
                        pt1[1], pt2[1], tmp_ys)
                    for idx in range(start_line_idx, end_line_idx):
                        tmp_pt1 = (pt1[0], tmp_ys[idx])
                        tmp_pt2 = (pt1[0], tmp_ys[idx + 1])
                        if (tmp_pt1, tmp_pt2) not in divider_list[i] and (tmp_pt2, tmp_pt1) not in divider_list[i]:
                            divider_list[i].append((tmp_pt1, tmp_pt2))
                elif pt1[1] == pt2[1]:  # same y
                    start_line_idx = -1
                    end_line_idx = -1

                    for idx in range(len(tmp_xs)):
                        if same(tmp_xs[idx], pt1[0]):
                            start_line_idx = idx
                        if same(tmp_xs[idx], pt2[0]):
                            end_line_idx = idx
                            break  # because it was sorted

                    assert start_line_idx != -1 and end_line_idx != -1, "error happend when building the frame of the table"
                    for idx in range(start_line_idx, end_line_idx):
                        tmp_pt1 = (tmp_xs[idx], pt1[1])
                        tmp_pt2 = (tmp_xs[idx + 1], pt1[1])
                        if (tmp_pt1, tmp_pt2) not in divider_list[i] and (tmp_pt2, tmp_pt1) not in divider_list[i]:
                            divider_list[i].append((tmp_pt1, tmp_pt2))
                else:
                    assert False, "seems that it is not a regular table"

        return divider_list

    def get_tables(self, layout,text_cols):

        # step 1
        bias, table_outline_elem_lst, table_raw_dash_lst, dashline_parser_xs, dashline_parser_ys = \
            self.get_tables_elements(layout,text_cols)

        # step 2
        table_dashlines = self.get_tables_dashlines(table_raw_dash_lst, bias)
        #print table_dashlines

        for idx,dashline in enumerate(table_dashlines):
            if dashline['x0'] not in dashline_parser_xs:
                dashline_parser_xs.append(dashline['x0'])
            if dashline['x1'] not in dashline_parser_xs:
                dashline_parser_xs.append(dashline['x1'])
            if dashline['y0'] not in dashline_parser_ys:
                dashline_parser_ys.append(dashline['y0'])
            if dashline['y1'] not in dashline_parser_ys:
                dashline_parser_ys.append(dashline['y1'])
        dashline_parser_xs.sort()
        dashline_parser_ys.sort()

        table_outline_elem_lst = self.get_tables_elements_all(table_outline_elem_lst, table_dashlines,
                                                              dashline_parser_xs, dashline_parser_ys)

        # step 3: 粗略分出不同表格的子区域
        clean_tables_lst = self.get_tables_areas(table_outline_elem_lst, bias)

        # Step 4: 然后规范一下坐标值
        # 开始整理表格内容
        print "number of potential tables in this page is {0}".format(len(clean_tables_lst))


        raw_lines, raw_points, points_visited = self.get_tables_raw_frame(clean_tables_lst, bias)


        # step 5
        table_list, table_line_list, divider_list = self.get_tables_init_info(raw_points, raw_lines, points_visited)

        # step 6
        divider_list = self.get_tables_divider_list(table_list, table_line_list, divider_list, bias)


        return table_list, bias, divider_list

    def add_cross_point(self, lines, points):

        local_lines = copy.copy(lines)
        tables = []
        #get tables
        while len(local_lines) > 0:
            top_y = 0
            table = []
            top_id = -1
            for i in range(len(local_lines)):
                l = local_lines[i]
                if l[0][1] == l[1][1]: #水平线
                    if l[0][1] > top_y:
                        top_y = l[0][1]
                        top_id = i
            bottom_y = top_y
            for j in range(len(local_lines)):
                l = local_lines[j]
                if l[0][0] == l[1][0]:  # 垂直线
                    #print max(l[0][1],l[1][1]),top_y,l
                    if same(top_y , max(l[0][1],l[1][1])):
                        if min(l[0][1],l[1][1]) < bottom_y:
                            bottom_y = min(l[0][1],l[1][1])
            if bottom_y == top_y:
                del local_lines[top_id]  # 移除页眉的线
                continue
            for k in range(len(local_lines)-1, -1, -1):
                l = local_lines[k]
                if min(l[0][1],l[1][1]) > bottom_y-1 and  max(l[0][1],l[1][1]) <top_y+1:
                    table.append(l)
                    del local_lines[k]

            tables.append(table)

        segs = []
        for idx,t_lines in enumerate(tables):
            x_lines = []
            y_lines = []
            points_od = {}
            x_seg_points = {}
            y_seg_points = {}
            for l in t_lines:
                if l[0][1] == l[1][1]:
                    x_lines.append(l)
                elif l[0][0] == l[1][0]:
                    y_lines.append(l)

            #找出最左，最右的垂直线

            left = 10000
            right = 0
            left_points = []
            right_points = []
            for x_l in x_lines:
                min_x = min(x_l[0][0], x_l[1][0])
                max_x = max(x_l[0][0], x_l[1][0])
                left = min(min_x, left)
                right = max(max_x, right)
                for y_l in y_lines:
                    k = (y_l[0][0],x_l[0][1])
                    # y_line
                    min_y = min(y_l[0][1], y_l[1][1])
                    max_y = max(y_l[0][1], y_l[1][1])
                    # x_line

                    if  (k[0] > min_x-1 and k[0]<max_x+1) and (k[1]>min_y-1 and k[1]<max_y +1):
                        points_od[k] = [0]
                y0 = x_l[0][1]
                left_points.append([min_x,y0])
                right_points.append([max_x,y0])

            if left is not 10000:
                for p in left_points:
                    points_od[(left,p[1])] = [0]
            if right is not 0:
                for p in right_points:
                    points_od[(right,p[1])]= [0]




            for k in points_od:
                if k[1] not in x_seg_points:
                    x_seg_points[k[1]] = []
                x_seg_points[k[1]].append(k[0])
            for y in x_seg_points:
                x_seg_points[y].sort()
                last_x= x_seg_points[y][0]
                for i in range(1,len(x_seg_points[y])):
                    segs.append([(last_x,y),(x_seg_points[y][i],y)])
                    last_x = x_seg_points[y][i]


            for k in points_od:
                if k[0] not in y_seg_points:
                    y_seg_points[k[0]] = []
                y_seg_points[k[0]].append(k[1])

            for x in y_seg_points:
                y_seg_points[x].sort()
                last_y = y_seg_points[x][0]
                for i in range(1, len(y_seg_points[x])):
                    segs.append([(x, last_y), (x, y_seg_points[x][i])])
                    last_y = y_seg_points[x][i]
        #print len(segs)
        return segs
