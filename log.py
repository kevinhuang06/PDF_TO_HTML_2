#coding=utf-8
import os
from datetime import datetime



class Log(object):

    def __init__(self, odir, task_name):

        self.func = [self.miner_error, self.empty, self.parse_error, self.success]
        self.miner_ex_log = self.full_path(odir, 'corrupted_pdf', task_name)
        self.empty_ex_log = self.full_path(odir, 'empty_ex', task_name)
        self.parse_ex_log = self.full_path(odir, 'parse_ex', task_name)
        self.success_log = self.full_path(odir, 'success', task_name)

    def full_path(self, l1_dir, l2_dir, basename):
        if not os.path.exists(os.path.join(l1_dir, l2_dir)):
            os.makedirs(os.path.join(l1_dir, l2_dir))
        return os.path.join(l1_dir, l2_dir, basename)

    def t(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def log(self, type, fname, info=''):
        self.func[type](fname, info)

    def miner_error(self, fname, info):
        with open(self.miner_ex_log, 'a') as f:
            f.write('{0}\t{1}\t{2}\n'.format(fname, info, self.t()))

    def empty(self, fname, info):
        with open(self.empty_ex_log, 'a') as f:
            f.write('{0}\t{1}\t{2}\n'.format(fname, info, self.t()))

    def parse_error(self, fname, info):
        with open(self.parse_ex_log, 'a') as f:
            f.write('{0}\t{1}\t{2}\n'.format(fname, info, self.t()))

    def success(self, fname, info):
        with open(self.success_log, 'a') as f:
            f.write('{0}\t{1}\t{2}\n'.format(fname, info, self.t()))
