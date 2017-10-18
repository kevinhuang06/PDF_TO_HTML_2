#coding=utf-8

from simple_pdf2html import *

def get_HTML_fname(pdf_name):
	parts = pdf_name.split('.')
	assert len(parts) == 2, "Could Only handle path with one '.'"
	return reduce(lambda x, y: x + y, parts[:-1] + ['_content.html'])


fname = 'data/table_example_16.PDF'
#fname = 'data2/2016-04-28-1202256878.PDF'

with simplePDF2HTML(fname, get_HTML_fname(fname)) as test:
	test.convert([3,5])


