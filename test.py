#!/usr/bin/env python

import os
import pdb
from ctags_cache import CtagsCache

print("test 1:")
cache = CtagsCache()
cache.update_file("test/test.c")
cache.printall()
cache.remove_file('test/test.c')
cache.printall()


print("test 2:")
cache = CtagsCache(['/home/lfw/works/linux-2.6/include', 'linux-2.6'])
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache.printall()
cache.remove_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache.remove_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache.remove_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.remove_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.printall()

print("test 3:")
import timeit

cb_header = r"""
import ctags_cache
cache = ctags_cache.CtagsCache(['/home/lfw/works/linux-2.6/include', 'linux-2.6'])
cache.printall()
"""

cb_body = "print(cache.find_tags('romfs_mtd'))"
cb_body = """
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
"""

print(timeit.Timer(cb_body, cb_header).timeit(1))

