#!/usr/bin/env python

__all__ = ['CtagsCache']

import os
import threading

from .file_node import FileNode
from .ctags_table import CtagsTable

class CtagsCacheWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self._run_cond = threading.Condition()
        self._run_func = None
        self.start()

    def work(self, func, wait_complete = 0):
        with self._run_cond:
            self._run_func = func
            self._run_cond.notify()
            if wait_complete:
                self._run_cond.wait_for(lambda: self._run_func == None)

    def run(self):
        with self._run_cond:
            while 1:
                self._run_cond.wait_for(lambda: self._run_func)
                self._run_func()
                self._run_func = None
                self._run_cond.notify()

class CtagsCache:

    def __init__(self, inclist = []):
        self._worker = CtagsCacheWorker()
        self._file_nodes = {}
        self._ctags_table = CtagsTable()
        self._init_inc_list(inclist)

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
            node = FileNode(path, self._inc_list)
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

    def _update_file(self, path):
        path = os.path.realpath(path)
        if not os.access(path, os.R_OK):
            return

        node = self._get_node(path, 1)
        if node.refcount <= 0:
            # a new node.
            node.refcount = 1
            new_deps = node.depends
            obsolete_deps = []
        else:
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

    def update_file(self, path):
        def run_func():
            self._update_file(path)

        self._worker.work(run_func)

    def remove_file(self, path):
        def run_func():
            self._remove_file(path)

        self._worker.work(run_func)

    def find_tags(self, name_prefix, match_whole = 0):
        res = []
        def run_func():
            nonlocal res
            res = self._ctags_table.find(name_prefix, match_whole)
        
        self._worker.work(run_func, 1)

        return res

    def printall(self):
        print('file nodes:', len(self._file_nodes),
              'files:', self._ctags_table.files(),
              'tags:', self._ctags_table.tags())

