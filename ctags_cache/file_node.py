#!/usr/bin/env python

import os

class FileNode:

    def __init__(self, path, inclist = []):
        self.path = path
        self.refcount = 0
        self.check_loop = 0
        self.depends = None
        
        self.renew_depends(inclist)

    def __str__(self):
        return self.path

    def _header_files(self, inclist):
        path_prefix = os.path.dirname(self.path)
        with open(self.path, 'r', encoding = "ascii", errors='ignore') as fobj:
            for line in fobj:
                line = line.lstrip()
                if not line.startswith("#"):
                    continue

                # skip "#" and space.
                line = line[1:].lstrip()
                if not line.startswith('include'):
                    continue

                # skip "include" and space.
                line = line[7:].lstrip()
                if not line:
                    continue

                if path_prefix in inclist:
                    inclist.remove(path_prefix)

                if line[0] == '"':
                    endchar = '"'
                    inclist.insert(0, path_prefix)
                elif line[0] == '<':
                    endchar = '>'
                    inclist.append(path_prefix)
                else:
                    continue

                end = line.find(endchar, 1)
                if end < 0:
                    continue

                # strip '"', '<>', and space.
                line = line[1:end].strip()
                if not line:
                    continue

                for incpath in inclist:
                    path = os.path.join(incpath, line)
                    if os.access(path, os.R_OK):
                        yield path
                        break

    def renew_depends(self, inclist = []):
        self.depends = frozenset(self._header_files(inclist))

if __name__ == "__main__":
    for f in FileNode('../test/test.c').depends:
        print(f)

