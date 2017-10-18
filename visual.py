#coding=utf-8

import time
from draw import Draw
from pdfminer.layout import *


def show_page_layout_points(layout, points, raw_lines=None):
    page_range = {
        "left": layout.x0,
        "right": layout.x1,
        "top": layout.y1,
        "bottom": layout.y0
    }

    # turtle.tracer(False)
    print "Page Range = left:{0}, right: {1}, top: {2}, bottom: {3}".format( \
        page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])
    offset_x = -1.0 * (page_range["right"] + page_range["left"]) / 2.0
    offset_y = -1.0 * (page_range["top"] + page_range["bottom"]) / 2.0
    size_x = 1.5 * (page_range["right"] - page_range["left"])
    size_y = 1.5 * (page_range["top"] - page_range["bottom"])
    draw = Draw(size_x, size_y, offset_x, offset_y)
    draw.set_color("black")
    draw.square(page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])

    for p in points:
        # for p in tp:
        x ,y = p[0] ,p[1]
        draw.dot(x ,y)
    if raw_lines:
        for p in raw_lines:
            draw.line(p[0][0], p[0][1], p[1][0], p[1][1])
    draw.done()
    time.sleep(10)

def show_page_layout_lines(layout, lines):
    page_range = {
        "left": layout.x0,
        "right": layout.x1,
        "top": layout.y1,
        "bottom": layout.y0
    }

    # turtle.tracer(False)
    print "Page Range = left:{0}, right: {1}, top: {2}, bottom: {3}".format( \
        page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])
    offset_x = -1.0 * (page_range["right"] + page_range["left"]) / 2.0
    offset_y = -1.0 * (page_range["top"] + page_range["bottom"]) / 2.0
    size_x = 1.5 * (page_range["right"] - page_range["left"])
    size_y = 1.5 * (page_range["top"] - page_range["bottom"])
    draw = Draw(size_x, size_y, offset_x, offset_y)
    draw.set_color("black")
    draw.square(page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])

    # for p in lines:
    # for p in tline['box']:
    # p = tline['box']
    #    draw.line(p[0][0], p[0][1], p[1][0], p[1][1])
    #    print p[0][0], p[0][1], p[1][0], p[1][1]
    #    draw.square(p[0][0],p[1][0], p[1][1],p[0][1])
    for p in lines:
        # for p in t_lines:
        draw.line(p['x0'], p['y0'], p['x1'], p['y1'])

    draw.done()
    time.sleep(10)
def show_page_layout_post(layout, lines):
    page_range = {
        "left": layout.x0,
        "right": layout.x1,
        "top": layout.y1,
        "bottom": layout.y0
    }

    # turtle.tracer(False)
    print "Page Range = left:{0}, right: {1}, top: {2}, bottom: {3}".format( \
        page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])
    offset_x = -1.0 * (page_range["right"] + page_range["left"]) / 2.0
    offset_y = -1.0 * (page_range["top"] + page_range["bottom"]) / 2.0
    size_x = 1.5 * (page_range["right"] - page_range["left"])
    size_y = 1.5 * (page_range["top"] - page_range["bottom"])
    draw = Draw(size_x, size_y, offset_x, offset_y)
    draw.set_color("black")
    draw.square(page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])

    for line in lines:
        for idx ,l in enumerate(line):
            if idx% 2 == 0:
                draw.set_color("orange")
            else:
                draw.set_color("red")
            left = l[0][0]
            right = l[1][0]
            bottom = l[0][1]
            top = l[1][1]

            draw.square(left, right, top, bottom)
    """
    for l in lines:
        draw.set_color("orange")
        left = l['x0']
        right = l['x1']
        top = l['y1']
        bottom = l['y0']
        isLine = l['isLine']
        print "left:{0}, right: {1}, top: {2}, bottom: {3}".format(left, right, top, bottom)
        if isLine == 'x':
            fixed_y = (top + bottom) / 2.0
            draw.line(left, fixed_y, right, fixed_y)
        elif isLine == 'y':
            fixed_x = (left + right) / 2.0
            draw.line(fixed_x, top, fixed_x, bottom)
        else:
            draw.square(left, right, top, bottom)
    """
    draw.done()
    time.sleep(10)


def show_page_layout(layout):
    page_range = {
        "left": layout.x0,
        "right": layout.x1,
        "top": layout.y1,
        "bottom": layout.y0
    }
    print "Page Range = left:{0}, right: {1}, top: {2}, bottom: {3}".format( \
        page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])
    offset_x = -1.0 * (page_range["right"] + page_range["left"]) / 2.0
    offset_y = -1.0 * (page_range["top"] + page_range["bottom"]) / 2.0
    size_x = 1.5 * (page_range["right"] - page_range["left"])
    size_y = 1.5 * (page_range["top"] - page_range["bottom"])
    draw = Draw(size_x, size_y, offset_x, offset_y)
    draw.set_color("black")
    draw.square(page_range["left"], page_range["right"], page_range["top"], page_range["bottom"])
    idx = 0
    for x in layout:
        isLine = False
        if (isinstance(x, LTTextBoxHorizontal)):

            for line in x:
                # print line # LTTextLine
                # draw.set_color("green")
                if line.x1 - line.x0 > 12:
                    draw.square(line.x0, line.x1, line.y1, line.y0)
                for char in line:
                    # print char # LTChar / LTAnno
                    if isinstance(char, LTChar):
                        draw.set_color("brown")
                        res = re.sub(r'\s+', '', char.get_text())
                        if len(res) > 0:
                            draw.square(char.x0, char.x1, char.y1, char.y0)
                        else:
                            print "#%s#" % char.get_text()
                        print char.get_text()
                    elif isinstance(char, LTChar):
                        draw.set_color("blue")
                        draw.square(char.x0, char.x1, char.y1, char.y0)
            draw.set_color("black")

            pass
        elif (isinstance(x, LTRect)):

            isLine = self.is_line(x)

            # if isLine:
            idx += 1
            if idx % 2 == 0:
                draw.set_color("orange")
            else:
                draw.set_color("red")
        else:
            # print x
            # raw_input()
            draw.set_color("blue")

        left = x.x0
        right = x.x1
        top = x.y1
        bottom = x.y0
        print "left:{0}, right: {1}, top: {2}, bottom: {3}".format(left, right, top, bottom)
        if isLine == 'x':
            fixed_y = (top + bottom) / 2.0
            draw.line(left, fixed_y, right, fixed_y)
        elif isLine == 'y':
            fixed_x = (left + right) / 2.0
            draw.line(fixed_x, top, fixed_x, bottom)
        else:
            pass
            # if (right - left) > 12:
            #    print right - left
            #    draw.square(left, right, top, bottom)

    draw.done()
    time.sleep(10)
    # return layout
