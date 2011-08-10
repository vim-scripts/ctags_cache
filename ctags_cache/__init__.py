#!/usr/bin/env python

__all__ = ['CtagsCache']

import os
import threading

from .file_node import FileContainer
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
        self._file_container = FileContainer()
        self._ctags_table = CtagsTable()
        self._set_include_list(inclist)

        self._worker = CtagsCacheWorker()

    def _set_include_list(self, inclist):
        self._include_list = []
        for incpath in inclist:
            incpath = os.path.realpath(incpath)
            if incpath not in self._include_list:
                self._include_list.append(incpath)

    def _add_file_recursively(self, path):
        node = self._file_container.get(path, 1)
        if node.refcount <= 0:
            node.refcount = 1
            node.check_loop = 1

            new_files = [path]
            for f in node.header_files(self._include_list):
                dep_node, new_dep_files = self._add_file_recursively(f)
                node.depends.append(dep_node)
                new_files += new_dep_files

            node.check_loop = 0
            return node, new_files

        elif not node.check_loop:
            node.refcount += 1
            return node, []

        else:
            return node, []

    def _remove_file_recursively(self, node):
        if node.refcount == 0:
            return []
        elif node.refcount > 1:
            node.refcount -= 1
            return []

        node.refcount = 0
        self._file_container.remove(node)

        obsolete_files =[node.path]
        for n in node.depends:
            obsolete_files += self._remove_file_recursively(n)

        return obsolete_files

    def _update_file(self, path):
        path = os.path.realpath(path)
        if not os.access(path, os.R_OK):
            return

        node = self._file_container.get(path, 1)
        if node.refcount <= 0:
            node.refcount = 1

        node.check_loop = 1

        new_depends = []
        new_files = [path]
        for f in node.header_files(self._include_list):
            dep_node = None
            for n in node.depends:
                if n.path == f:
                    dep_node = n
                    break

            if not dep_node:
                dep_node, new_dep_files = self._add_file_recursively(f)
                new_files += new_dep_files

            new_depends.append(dep_node)

        obsolete_files = [path]
        for old_node in node.depends:
            if old_node not in new_depends:
                obsolete_files += self._remove_file_recursively(old_node)

        node.check_loop = 0
        node.depends = new_depends

        self._ctags_table.delete(obsolete_files)
        self._ctags_table.add(new_files)

    def update_file(self, path):
        def run_func():
            self._update_file(path)

        self._worker.work(run_func)

    def _remove_file(self, path):
        path = os.path.realpath(path)
        node = self._file_container.get(path)
        if node:
            obsolete_files = self._remove_file_recursively(node)
            self._ctags_table.delete(obsolete_files)

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
        print('files:', self._file_container.size(), 'tags:', self._ctags_table.tags())

