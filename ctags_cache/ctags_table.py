#!/usr/bin/env python

import subprocess

from .utils import binary_search

CTAGS_CMD = 'ctags --fields=fksSzt --extra=+q --c-kinds=+p -n -u -L - -f -'

def parse_ctags_line(line):
    """
    parse tags file's line then return result.

    the result is a dict which has many fields: name, path, address, kind,
    scope, signature, typeref, etc.
    """

    res = {}

    idx = line.find('\t')
    res['name'] = line[:idx]
    
    start = idx + 1
    idx = line.find('\t', start)
    res['path'] = line[start:idx]

    start = idx + 1
    idx = line.find(';"\t', start)
    res['address'] = line[start:idx]

    start = idx + 3

    while True:
        idx = line.find(':', start)
        if idx < 0:
            print("warning: unknown ctags ouput format!")
            break
        
        field = line[start:idx]
        start = idx + 1

        idx = line.find('\t', start)
        if idx < 0:
            # don't forget newline and EOF.
            idx = len(line) - 1

        value = line[start:idx]
        start = idx + 1

        res[field] = value

        if start == len(line):
            break
    
    return res

def make_search_matcher(field, target, match):
    def matcher(key):
        if match(key[field], target):
            return '='
        elif key[field] > target:
            return '>'
        elif key[field] < target:
            return '<'

    return matcher

class CtagsTable:

    def __init__(self):
        self._tag_list = []
        self._file_list = []

    def tags(self):
        return len(self._tag_list)

    def files(self):
        return len(self._file_list)

    def delete(self, file_list):
        deleted_tags = 0
        deleted_files = 0
        for path in file_list:
            matcher = make_search_matcher('path', path, lambda x, y: x == y)
            idx = binary_search(self._file_list, matcher)
            if idx == None:
                continue

            for tag in self._file_list[idx]['tags']:
                tag['name'] = '\255'
                deleted_tags += 1

            self._file_list[idx]['path'] = '\255'
            deleted_files += 1

        if deleted_tags:
            self._tag_list.sort(key = lambda x: x['name'])
            self._tag_list[-deleted_tags:] = []

        if deleted_files:
            self._file_list.sort(key = lambda x: x['path'])
            self._file_list[-deleted_files:] = []

    def add(self, file_list):
        p = subprocess.Popen(CTAGS_CMD, shell = True, stdin = subprocess.PIPE, 
                stdout = subprocess.PIPE)
        p.stdin.write('\n'.join(file_list).encode('utf-8'))
        p.stdin.close()

        f = None
        for line in p.stdout:
            ret = parse_ctags_line(line.decode('utf-8'))
            self._tag_list.append(ret)

            if not f or f['path'] != ret['path']:
                f = {}
                f['path'] = ret['path']
                f['tags'] = []
                self._file_list.append(f)

            f['tags'].append(ret)

        p.stdout.close()

        self._tag_list.sort(key = lambda x: x['name'])
        self._file_list.sort(key = lambda x: x['path'])

    def find(self, name_prefix, match_whole):
        if not match_whole:
            matcher = make_search_matcher('name', name_prefix,
                    lambda x, y: x.startswith(y))
        else:
            matcher = make_search_matcher('name', name_prefix,
                    lambda x, y: x == y)

        idx = binary_search(self._tag_list, matcher)
        if idx == None:
            return []

        res = []
        for tag in self._tag_list[idx:]:
            if matcher(tag) != '=':
                break

            res.append(tag)

        return res

    def printall(self):
        for tag in self._tag_list:
            print(tag)

if __name__ == "__main__":
    cb_header = """
import subprocess
import ctags_table
cmd = "find ../test -name '*.[ch]'"
p = subprocess.Popen(cmd, shell = True, stdin = subprocess.PIPE,
        stdout = subprocess.PIPE)
li = [ line.decode('utf-8').strip() for line in p.stdout ]
tbl = ctags_table.CtagsTable()
tbl.add(li)
print('tags:', tbl.tags(), 'files:', tbl.files())
    """

    cb_body = "tbl.delete(li[0:1]); print(tbl.tags())"
    cb_body = "tbl.add(li[0:1]); print(tbl.tags())"
    cb_body = "print(tbl.find('simple_init'))"

    import timeit

    print(timeit.Timer(cb_body, cb_header).timeit(1))

