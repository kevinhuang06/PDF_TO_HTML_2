#coding=utf-8

import glob

from simple_pdf2html import *

def get_HTML_fname(pdf_name):
	parts = pdf_name.split('.')
	return reduce(lambda x, y: x + y, parts[:-1] + ['_content.html'])

name_list = []
#fname = 'data/table_example_16.PDF'
fname = 'pdf_image/2016-01-28-1201949742.PDF'
#fname = 'data2/2016-04-28-1202256878.PDF'
#fname = 'data2/2015-12-30-1201882111.PDF'

for name in glob.glob('data/2017-03-30-1203224890.PDF'):
	name_list.append(name)
name_list.append(fname)
for i, fname in enumerate(name_list):
	with simplePDF2HTML(fname, get_HTML_fname(fname)) as test:
		# 这个参数会影响到，表格推导时 相邻点的合并， 表格回填时 单元格定位（不应该用这个）
		bias = [2, 3]#[[2, 3], [1.5, 2], [3, 5]]
		test.convert(bias)

