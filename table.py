#coding=utf-8

import re
import copy

class TableFrame(object):
    def __init__(self, table_points_list, bias, table_divider_list):
        # assert len(table_points_list) > 2, "the data passed in is not a table at all"
        self.bias = bias
        self.grids = {"x": [], "y": []}
        self.data = []  # content, [['XXX', 'XXX'],['XXX', 'XXX']...]
        self.font = []
        self.rowspan = []
        self.colspan = []
        self.location_map = {}  # content: [(x_location, y_location): (x_data, y_data)]
        self.range = {"max_x": -1, "max_y": -1, "min_x": 0, "min_y": 0}
        for point in table_points_list:
            x = point[0]
            y = point[1]
            if x not in self.grids['x']:
                self.grids['x'].append(x)
            if y not in self.grids['y']:
                self.grids['y'].append(y)
        self.grids['x'].sort()
        self.grids['y'].sort(reverse=True)
        # print self.grids['x']
        # print self.grids['y']
        # assert len(self.grids['x']) > 1 and len(self.grids['y']) > 1, "the table data does not represent an area"
        #两个点确定一个单元格？ 处于同一条线上的不行
        if len(table_points_list) <= 2 or len(self.grids['x']) <= 1 or len(self.grids['y']) <= 1:
            self.grids = None
        else:
            # get the structure of the table
            # print table_divider_list
            n_rows = len(self.grids['y']) - 1
            n_cols = len(self.grids['x']) - 1
            for i in range(n_rows):
                empty_line = []
                empty_font = []
                empty_rowspan = []
                empty_colspan = []
                tmp_col = 0
                for j in range(n_cols):
                    # print "up, down, left, right"
                    # print self.grids['y'][i], self.grids['y'][i + 1], self.grids['x'][j], self.grids['x'][j + 1]
                    upperleft_corner = (self.grids['x'][j], self.grids['y'][i])
                    lowerleft_corner = (self.grids['x'][j], self.grids['y'][i + 1])
                    upperright_corner = (self.grids['x'][j + 1], self.grids['y'][i])
                    lowerright_corner = (self.grids['x'][j + 1], self.grids['y'][i + 1])
                    upper_connected = False
                    left_connected = False

                    if i > 0:
                        # possible that rowspan > 0
                        if (upperleft_corner, upperright_corner) not in table_divider_list and \
                                        (upperright_corner, upperleft_corner) not in table_divider_list:
                            # connected to the upper grid
                            upper_connected = True
                    if j > 0:
                        # possible that colspan > 0
                        if (lowerleft_corner, upperleft_corner) not in table_divider_list and \
                                        (upperleft_corner, lowerleft_corner) not in table_divider_list:
                            # connected to the left grid
                            left_connected = True

                    # print i, j, upper_connected, left_connected

                    # upper_connected = False
                    # left_connected = False
                    # print "point({2},{3}) upper_connected={0}, left_connected={1}".format(upper_connected, left_connected, i, j)
                    '''if i == 2 and j == 1:
                        print upper_connected
                        print (upperleft_corner, upperright_corner)
                        print (upperright_corner, upperleft_corner)
                        table_divider_list.sort()
                        print table_divider_list
                        print n_cols, n_rows
                        print self.grids['y']
                        '''

                    if upper_connected and left_connected:
                        self.location_map[(i, j)] = self.location_map[(i - 1, j)]
                    elif upper_connected:
                        self.location_map[(i, j)] = self.location_map[(i - 1, j)]
                        # print "self.location_map[({0}, {1})] = ({2}, {3})".format(i, j, self.location_map[i-1, j][0], self.location_map[i-1, j][1])
                        representer_i = self.location_map[(i - 1, j)][0]
                        representer_j = self.location_map[(i - 1, j)][1]
                        self.rowspan[representer_i][representer_j] += 1

                    elif left_connected:
                        self.location_map[(i, j)] = self.location_map[i, (j - 1)]
                        # print "self.location_map[({0}, {1})] = ({2}, {3})".format(i, j, self.location_map[i, (j - 1)][0], self.location_map[i, (j - 1)][1])
                        representer_i = self.location_map[(i, j - 1)][0]
                        representer_j = self.location_map[(i, j - 1)][1]
                        # self.colspan[representer_i][representer_j] += 1
                        '''
                        print len(empty_colspan)
                        print representer_j
                        print i, j, tmp_col
                        print empty_colspan
                        # '''
                        empty_colspan[representer_j] += 1

                    else:  # the starting grid of an area
                        empty_line.append([])
                        empty_font.append(None)
                        empty_rowspan.append(1)
                        empty_colspan.append(1)
                        # print "self.location_map[({0}, {1})] = ({2}, {3})".format(i, j, i, tmp_col)
                        self.location_map[(i, j)] = (i, tmp_col)
                        tmp_col += 1
                # print "empty colspan"
                # print empty_colspan
                self.data.append(empty_line)
                self.font.append(empty_font)
                self.rowspan.append(empty_rowspan)
                self.colspan.append(empty_colspan)
            # print self.rowspan
            # print self.colspan
            corner1 = table_points_list[0]
            corner2 = table_points_list[len(table_points_list) - 1]
            self.range['max_x'] = max(corner1[0], corner2[0])
            self.range['max_y'] = max(corner1[1], corner2[1])
            self.range['min_x'] = min(corner1[0], corner2[0])
            self.range['min_y'] = min(corner1[1], corner2[1])

    def locate(self, point):
        def greater_than(a, b):
            if a + self.bias > b:
                return True
            return False

        def smaller_than(a, b):
            if a < b + self.bias:
                return True
            return False

        # point: (x, y)
        x = point[0]
        y = point[1]
        x_idx = -1
        y_idx = -1
        n_x = len(self.grids['x'])
        n_y = len(self.grids['y'])
        # print n_x, n_y
        # print self.grids['x']
        # print self.grids['y']
        for i in range(1, n_x):
            if greater_than(x, self.grids['x'][i - 1]) and smaller_than(x, self.grids['x'][i]):
                x_idx = i - 1
                break
        for i in range(1, n_y):
            if smaller_than(y, self.grids['y'][i - 1]) and greater_than(y, self.grids['y'][i]):
                y_idx = i - 1
                break
        # print x_idx, y_idx
        if x_idx == -1 or y_idx == -1:
            return None
        (row, col) = self.location_map[(y_idx, x_idx)]
        return (row, col)  # row, col

    def get_clean_data(self):
        clean_data = []
        clean_fonts = []
        clean_rowspan = []
        clean_colspan = []
        for i in range(len(self.data)):
            line = self.data[i]
            empty = True
            for elem in line:
                if len(elem):
                    empty = False
                    break
            if not empty:
                clean_data.append(copy.copy(line))
                clean_fonts.append(copy.copy(self.font[i]))
                clean_rowspan.append(copy.copy(self.rowspan[i]))
                clean_colspan.append(copy.copy(self.colspan[i]))
        return clean_data, clean_fonts, clean_rowspan, clean_colspan

    def is_in_range(self, point):
        def greater_than(a, b):
            if a + self.bias > b:
                return True
            return False

        def smaller_than(a, b):
            if a < b + self.bias:
                return True
            return False

        # point: (x, y)
        x = point[0]
        y = point[1]
        x_idx = -1
        if greater_than(x, self.range['min_x']) and smaller_than(x, self.range['max_x']) \
                and greater_than(y, self.range['min_y']) and smaller_than(y, self.range['max_y']):
            return True
        return False

    def add_data(self, location, content):
        row = location[0]
        col = location[1]
        self.data[row][col].append(content)

    def included_in_table(self, another_table):
        corner1 = (self.range['min_x'], self.range['min_y'])
        corner2 = (self.range['max_x'], self.range['min_y'])
        return another_table.is_in_range(corner1) and another_table.is_in_range(corner2)

    def dumps_to_html(self, page_xrange=None):
        # data = table_frame.data
        html = []
        data, font, rowspan, colspan = self.get_clean_data()
        if page_xrange:
            width_portion = 100.0 * (self.range['max_x'] - self.range['min_x']) / (
                page_xrange[1] - page_xrange[0])
            html.append('<table border="1" cellspacing="0" align="center" width="{0}%">'.format(int(width_portion)))
        else:
            html.append('<table border="1" cellspacing="0" align="center">')

        for i in range(len(data)):
            html.append('<tr>')

            for j in range(len(data[i])):
                content = data[i][j]
                fontsize = font[i][j]
                rs = rowspan[i][j]
                cs = colspan[i][j]
                candy = 'align=\"middle\"'
                res = re.search(r'[%\d,\.-]+', "".join(content))

                if res and res.group() == "".join(content):
                    candy = 'align=\"right\"'

                if fontsize:
                    html.append('<td  rowspan="{1}" colspan="{2}" {3}>{0}</td>'.format(
                        "<br>".join(content), rs, cs, candy))
                else:
                    html.append(
                        '<td rowspan="{1}" colspan="{2}" {3}>{0}</td>'.format("<br>".join(content), rs, cs, candy))
            html.append('</tr>')

        html.append('</table>')

        return html