#coding=utf-8

import turtle # 为了可视化显示检测到的布局

class Draw(object):
    def __init__(self, size_x, size_y, offset_x, offset_y):
        self.offset_x = offset_x
        self.offset_y = offset_y
        turtle.clear()
        turtle.speed(0)
        turtle.screensize(canvwidth=size_x, canvheight=size_y, bg=None)

    def done(self):
        turtle.done()

    def set_color(self, color_string):
        turtle.pencolor(color_string)

    def dot(self, x, y, size=3, color_string="purple"):
        # turtle.penup()
        turtle.goto(x + self.offset_x, y + self.offset_y)
        # turtle.pendown()
        turtle.dot(size, color_string)

    # turtle.penup()
    def line(self, start_x, start_y, end_x, end_y):
        turtle.penup()
        turtle.goto(start_x + self.offset_x, start_y + self.offset_y)
        turtle.pendown()
        self.dot(start_x, start_y)
        turtle.goto(end_x + self.offset_x, end_y + self.offset_y)
        turtle.penup()

    def square(self, left, right, top, bottom):
        turtle.penup()
        turtle.goto(left + self.offset_x, top + self.offset_y)
        turtle.pendown()
        turtle.goto(right + self.offset_x, top + self.offset_y)
        turtle.goto(right + self.offset_x, bottom + self.offset_y)
        turtle.goto(left + self.offset_x, bottom + self.offset_y)
        turtle.goto(left + self.offset_x, top + self.offset_y)
        turtle.penup()