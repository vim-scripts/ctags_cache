#!/usr/bin/env python

import re
import os

FILE_TYPES = [
    {
        'suffix': r'\.[ch]$',
        'include': r'^\s*#\s*include\s+(\"|\<)\s*([\w\.\/]+)\s*(?:\"|\>)\s*$'
    },
]

for ft in FILE_TYPES:
    ft['suffix_regexp'] = re.compile(ft['suffix'])
    ft['include_regexp'] = re.compile(ft['include'])

class FileNode():

    def __init__(self, path):
        self.path = path
        self.refcount = 0
        self.check_loop = 0
        self.depends = []

        self._include_regexp = None
        for ft in FILE_TYPES:
            if ft['suffix_regexp'].search(path):
                self._include_regexp = ft['include_regexp']
                break

    def __str__(self):
        return self.path

    def header_files(self, inclist = []):
        if not self._include_regexp:
            return

        path_prefix = os.path.dirname(self.path)
        with open(self.path, 'r', encoding = "ascii", errors='ignore') as fobj:
            for line in fobj:
                ret = self._include_regexp.match(line)
                if not ret:
                    continue
                
                if path_prefix in inclist:
                    inclist.remove(path_prefix)

                if ret.group(1) == '"':
                    inclist.insert(0, path_prefix)
                else:
                    inclist.append(path_prefix)

                for incpath in inclist:
                    path = os.path.join(incpath, ret.group(2))
                    if os.access(path, os.R_OK):
                        yield path
                        break

class FileContainer:

    def __init__(self):
        self._file_list = []

    def __iter__(self):
        return iter(self._file_list)

    def size(self):
        return len(self._file_list)
    
    def has(self, node):
        return node in self._file_list

    def remove(self, node):
        return self._file_list.remove(node)
    
    def get(self, path, create_new = 0):
        for node in self._file_list:
            if node.path == path:
                return node

        if create_new:
            node = FileNode(path)
            self._file_list.append(node)
            return node

        return None

    def printall(self):
        if self._file_list == []:
            print("empty")

        for line in self._file_list:
            print(line)

if __name__ == "__main__":
    for f in FileNode('../test/test.c').header_files():
        print(f)

