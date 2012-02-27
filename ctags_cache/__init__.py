#!/usr/bin/env python

__all__ = ['CtagsCache']

import os
import threading

from .file_node import get_file_class
from .ctags_table import CtagsTable

class CtagsCacheWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self._works_cond = threading.Condition()
        self._works = []
        self._barrier = 0
        self.start()

    def add_work(self, new):
        with self._works_cond:
            if new['op'] == 'wait_all_complete':
                self._barrier = 1
                self._works.append(new)
                self._works_cond.notify()
                self._works_cond.wait_for(lambda: not self._barrier)

            else:
                dup = None
                for w in self._works:
                    if w['target'] != new['target']:
                        continue

                    elif (new['op'] == 'add' and w['op'] == 'remove') or \
                         (new['op'] == 'remove' and w['op'] == 'add') or \
                         (new['op'] == 'update' and w['op'] == 'update'):
                        dup = w

                if dup:
                    self._works.remove(dup)
                else:
                    self._works.append(new)

                self._works_cond.notify()

    def run(self):
        while 1:
            with self._works_cond:
                self._works_cond.wait_for(lambda: self._works)

                work = None
                if self._barrier:
                    for w in self._works:
                        w['run']()

                    self._works = []
                    self._barrier = 0

                else:
                    work = self._works.pop(0)

                self._works_cond.notify()

            if work:
                work['run']()

class FileTypeError(Exception):
    pass

class CtagsCache:

    def __init__(self, filetype, inclist = []):
        self._worker = CtagsCacheWorker()
        self._file_nodes = {}
        self._ctags_table = CtagsTable()
        self._init_inc_list(inclist)
        self._file_class = get_file_class(filetype)

        if not self._file_class:
            raise FileTypeError

    def _init_inc_list(self, inclist):
        self._inc_list = []
        for path in inclist:
            path = os.path.realpath(path)
            if path not in self._inc_list:
                self._inc_list.append(path)

    def _get_node(self, path, create_new = 0):
        node = None
        if path in self._file_nodes:
            node = self._file_nodes[path]
        elif create_new:
            node = self._file_class(path, self._inc_list)
            self._file_nodes[path] = node

        return node

    def _add_file_recursively(self, path):
        node = self._get_node(path, 1)
        if node.refcount <= 0:
            node.refcount = 1
            node.check_loop = 1

            new_files = [path]
            for f in node.depends:
                new_files += self._add_file_recursively(f)

            node.check_loop = 0
            return new_files
        elif not node.check_loop:
            node.refcount += 1
            return []
        else:
            return []

    def _remove_file_recursively(self, path):
        node = self._get_node(path)
        if not node:
            return []

        if node.refcount == 0:
            # impossible!
            print("what the fuck?!")
            return []
        elif node.refcount > 1:
            node.refcount -= 1
            return []

        node.refcount = 0
        del self._file_nodes[path]

        obsolete_files = [path]
        for f in node.depends:
            obsolete_files += self._remove_file_recursively(f)

        return obsolete_files

    def _add_file(self, path):
        path = os.path.realpath(path)
        if not os.access(path, os.R_OK):
            return

        node = self._get_node(path, 1)
        if node.refcount > 0:
            node.refcount += 1
            return

        # a new node.
        node.refcount = 1
        new_deps = node.depends

        node.check_loop = 1

        new_files = [path]
        for f in new_deps:
            new_files += self._add_file_recursively(f)

        node.check_loop = 0

        self._ctags_table.add(new_files)

    def _update_file(self, path):
        path = os.path.realpath(path)
        if not os.access(path, os.R_OK):
            return

        node = self._get_node(path)
        if not node:
            return

        old_depends = node.depends
        node.renew_depends(self._inc_list)
        new_deps = node.depends - old_depends
        obsolete_deps = old_depends - node.depends

        node.check_loop = 1

        new_files = [path]
        for f in new_deps:
            new_files += self._add_file_recursively(f)

        node.check_loop = 0

        obsolete_files = [path]
        for f in obsolete_deps:
            obsolete_files += self._remove_file_recursively(f)

        self._ctags_table.delete(obsolete_files)
        self._ctags_table.add(new_files)

    def _remove_file(self, path):
        path = os.path.realpath(path)
        obsolete_files = self._remove_file_recursively(path)
        self._ctags_table.delete(obsolete_files)

    def add_files(self, pathes):
        def run_func():
            for path in pathes:
                self._add_file(path)

        work = {}
        work["op"] = 'add'
        work['target'] = pathes
        work['run'] = run_func
        
        self._worker.add_work(work)

    def update_files(self, pathes):
        def run_func():
            for path in pathes:
                self._update_file(path)

        work = {}
        work["op"] = 'update'
        work['target'] = pathes
        work['run'] = run_func

        self._worker.add_work(work)

    def remove_files(self, pathes):
        def run_func():
            for path in pathes:
                self._remove_file(path)

        work = {}
        work["op"] = 'remove'
        work['target'] = pathes
        work['run'] = run_func

        self._worker.add_work(run_func)

    def find_tags(self, name_prefix, match_whole = 0):
        res = None
        def run_func():
            nonlocal res
            res = self._ctags_table.find(name_prefix, match_whole)

        work = {}
        work["op"] = 'wait_all_complete'
        work['target'] = None
        work['run'] = run_func
        
        self._worker.add_work(work)

        return res

    def printall(self):
        print('file nodes:', len(self._file_nodes),
              'files:', self._ctags_table.files(),
              'tags:', self._ctags_table.tags())

