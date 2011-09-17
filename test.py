#!/usr/bin/env python

import os
import pdb
import time
from ctags_cache import CtagsCache

print("test 1:")
cache = CtagsCache()
cache._update_file("test/test.c")
cache.printall()
cache._remove_file('test/test.c')
cache.printall()

print("test 2:")
cache = CtagsCache(['/home/lfw/works/linux-2.6/include', 'linux-2.6'])
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache.printall()
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache.printall()

print("test 3:")
import timeit

cb_header = r"""
import ctags_cache
cache = ctags_cache.CtagsCache(['/home/lfw/works/linux-2.6/include', 'linux-2.6'])
"""

cb_body = "print(cache.find_tags('romfs_mtd'))"
cb_body = r"""
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
cache._update_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/super.c')
cache._remove_file('/home/lfw/works/linux-2.6/fs/romfs/storage.c')
"""

print(timeit.Timer(cb_body, cb_header).timeit(1))

