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

class FileNode:

    def __init__(self, path, inclist = []):
        self._include_regexp = None
        for ft in FILE_TYPES:
            if ft['suffix_regexp'].search(path):
                self._include_regexp = ft['include_regexp']
                break

        self.path = path
        self.refcount = 0
        self.check_loop = 0
        self.depends = None
        
        self.renew_depends(inclist)

    def __str__(self):
        return self.path

    def _header_files(self, inclist):
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

    def renew_depends(self, inclist = []):
        self.depends = frozenset(self._header_files(inclist))

if __name__ == "__main__":
    for f in FileNode('../test/test.c').depends:
        print(f)

