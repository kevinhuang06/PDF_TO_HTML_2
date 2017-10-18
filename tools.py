#coding=utf-8


from pdfminer.layout import *



def same(x,y):
    return abs(x-y) < 1.1

def split_lines(slash_elem_lst):
    sv_line = []
    segs = []
    if len(slash_elem_lst) > 0:

        for item in sorted(slash_elem_lst.iteritems(), key=lambda x: x[0][0]):
            sv_line.append(item[0])

        last_l = sv_line[0]
        for i in range(len(sv_line)):
            if sv_line[i][0] <  last_l[1] + 12: #未超过一个字符
                last_l = [last_l[0], max(last_l[1], sv_line[i][1])]
            else:
                segs.append(last_l)
                last_l = sv_line[i]
        segs.append(last_l)
    return segs


def merge_same_line(raw_lines) :
    x_lines = {}
    y_lines = {}
    lines = []
    for p in raw_lines:
        if p[0][1] == p[1][1]:   # 水平线
            if p[0][1] not in x_lines:
                x_lines[p[0][1]] = []
            x_lines[p[0][1]].extend([p[0][0],p[1][0]])
        if p[0][0] == p[1][0]: # 垂直线
            if p[0][0] not in y_lines:
                y_lines[p[0][0]] = []
            y_lines[p[0][0]].extend([p[0][1], p[1][1]])

    for k in x_lines:
        x_lines[k].sort()

        start_p = x_lines[k][0]
        last_p = start_p
        for i in range(1, len(x_lines[k])):
            curr = x_lines[k][i]
            if curr - last_p > 2:#紧邻
                lines.append(([start_p,k],[last_p,k]))
                start_p = curr
            last_p = curr

    for k in y_lines:
        y_lines[k].sort()
        lines.append(([k, y_lines[k][0]],
                      [k, y_lines[k][-1]]))
    return lines

# a and sub is order list
def is_sub_list(a, sub):
    s = 0
    try:
         while  s <len(a) and not same(a[s], sub[0]):
            s +=1
    except Exception,ex:
        pass
    if len(a) - s < len(sub):
        return False
    flag = True
    for i,v in enumerate(sub):
        if not same(a[s+i], sub[i]):
            flag = False
            break
    return flag







def sheet_head_split(t):
    #第一行和第二行 分段数不同

    if len(t) >= 2:
        l1 = t[-1][1]
        l2 = t[-2][1]
        start = 0 # 记录最后一次相等的点
        # 检查表头点的一致性
        for i in range(len(l1)):
            if l1[i] not in l2:
                dis = abs(l1[-1] - l1[0])
                best_p = None
                for p in l2:
                    if abs(p - l1[i]) < dis:
                        dis = abs(p - l1[i])
                        best_p = p
                if best_p is None:
                    return None
                elif best_p not in l1:
                    l1.append(best_p)

        if len(l1) != len(l2):
            for i in range(min(len(l1),len(l2))):
                if not same(l1[i], l2[i]):
                    break
                start = i  # record the same location
            y = min(t[-1][0]-20, (t[-1][0]+t[-2][0])/2)
            return [y, l1, start]
    return None


def merge_ys(t):
    last_idx = 0
    remove_idx = []
    for curr in range(1,len(t)):
        if abs(t[last_idx][0] - t[curr][0])<10: # 小于一个字符
            if len(t[last_idx]) == 3 and t[last_idx][2] =='text': #优先保留文本计算出的行
                remove_idx.append(curr)
            else:
                remove_idx.append(last_idx)
                last_idx = curr
        else:
            last_idx = curr
    for idx in remove_idx[::-1]:
        del t[idx]



def uniform_segs(t):
    last_line = t[0]
    left = last_line[1][0]
    right = last_line[1][-1]
    for idx in range(1, len(t)):  # every line
        line = t[idx]
        left = min(left, line[1][0])
        right = max(right, line[1][-1])
        for i, new_p in enumerate(line[1]):  # 每一个点
            for p in last_line[1]:
                if same(new_p, p):
                    t[idx][1][i] = p
                    break
        last_line = line
    # 确保线到达左右边界
    for idx in range(len(t)):
        if same(left, t[idx][1][0]):
            t[idx][1][0] = left #保证
        else:
            t[idx][1].insert(0, left)
        if same(right, t[idx][1][-1]):
            t[idx][1][-1] = right
        else:
            t[idx][1].append(right)


def add_segs(xs,y,table_outline_elem_lst):
    last_x = xs[0]
    for i in range(len(xs)):
        tmp_elem = {
            'x0': last_x,
            'x1': xs[i],
            'y0': y,
            'y1': y,
            'isLine': 'x'
        }
        last_x = xs[i]
        table_outline_elem_lst.append(tmp_elem)

def in_range(value , bottom, up):
    b = min( bottom, up)
    u = max( bottom, up)
    if value > b and  value< u:
        return True
    return False



def get_corners(line, flag):
    text = ""
    char_list = []
    for char in line:
        if isinstance(char, LTChar):
            if u''!=char.get_text().strip():
                char_list.append(char)
            text += char.get_text()

    #if flag:
    #    print text


    if len(char_list) > 0:
        return (char_list[0].x0, line.y0),(char_list[-1].x1,line.y1),False

    return (line.x0,line.y0) , (line.x1,line.y1),True

def same_row(line, new_line):
    bottom = line['box'][0][1]
    up = line['box'][1][1]

    #有一个点在 range中，就认为是相同的线
    if new_line['box'][0][1]  > bottom-1 and new_line['box'][0][1]  < up+1:
        return True
    if new_line['box'][1][1]  > bottom-1 and new_line['box'][1][1]  < up+1:
        return  True

    return  False

def same_cols(line, new_line):
    left = line[0][0]
    right = line[1][0]

    if new_line[0][0]  > left-1 and new_line[0][0]  < right+1:
        return True
    if new_line[1][0]  > left-1 and new_line[1][0]  < right+1:
        return  True

    return  False

def parse_page_to_lines(layout):
    page_lines = []

    for x in layout:
        if (isinstance(x, LTTextBoxHorizontal)):

            for miner_line in x:
                if (isinstance(miner_line, LTTextLineHorizontal)):
                    corner_ld, corner_ru, empty = get_corners(miner_line, False)
                    #if empty:
                    #    continue
                    new_line = { 'box': [[corner_ld[0],corner_ld[1]], [corner_ru[0],corner_ru[1]]], \
                                 'text_lines': [(corner_ld, corner_ru)]}

                    for line in page_lines:
                        if same_row(line, new_line):
                            #合并的line, 更新数据
                            # p0.x, p0.y
                            line['box'][0][0] = min(line['box'][0][0], new_line['box'][0][0])
                            line['box'][0][1] = min(line['box'][0][1], new_line['box'][0][1])
                            # p1.x, p1.y
                            line['box'][1][0] = max(line['box'][1][0], new_line['box'][1][0])
                            line['box'][1][1] = max(line['box'][1][1], new_line['box'][1][1])
                            # find corresponding cols
                            for idx,l in enumerate(line['text_lines']):
                                if same_cols(l,new_line['box']):
                                    #merge two text line ,防止文字多的行，被选为最大列
                                    line['text_lines'][idx] =[
                                        (min(line['text_lines'][idx][0][0] , new_line['box'][0][0]),min(line['text_lines'][idx][0][1] , new_line['box'][0][1])),\
                                        (max(line['text_lines'][idx][1][0], new_line['box'][1][0]),max(line['text_lines'][idx][1][1], new_line['box'][1][1]))
                                    ]
                                    new_line = None
                                    break
                            if new_line:
                                line['text_lines'].append(new_line['text_lines'][0])
                                get_corners(miner_line, True)
                                new_line = None
                            break


                    #没找到可以合并的line
                    if new_line:
                        page_lines.append(new_line)
                    if len(page_lines) == 11:
                        pass
    len_last_line = 1
    tables = []
    text_cols = []

    left_bound = 10000
    right_bound = 0

    for l in page_lines:
        #print l['box'][1][1] - l['box'][0][1], len(l['text_lines']),  l['box'][1][0] - l['box'][0][0]
        if left_bound > l['box'][0][0]:
            left_bound = l['box'][0][0]
        if right_bound < l['box'][1][0]:
            right_bound = l['box'][1][0]

        if len(l['text_lines']) > 1:
            text_cols.append(l)
            if len_last_line > 1:
                tables[-1].append(l)
            else:
                tables.append([l])
        len_last_line = len(l['text_lines'])
    #到这里就可以画出所有的水平线了
    #print len(tables)
    table_bound = []
    for t in tables:
        box = t[0]['box']
        for i in range(1,len(t)):
            row = t[i]['box']
            box[0][0] = min(box[0][0], row[0][0])
            box[0][1] = min(box[0][1], row[0][1])
            box[1][0] = max(box[1][0], row[1][0])
            box[1][1] = max(box[1][1], row[1][1])
        table_bound.append(box)

    # merge cols
    return page_lines, text_cols