#!/usr/bin/env python

"""
The utils module supplied some tools.
"""

def binary_search(li, matcher):
    """
    find position in li, where matcher() first returns '='.

    the matcher() receives a argument which is the element in list 'li',
    and returns '=', '<', '>' to indicates match result.

    for example, we can define a matcher() to match number 1:
        def matcher(key):
            if key == 1:
                return '='
            elif key > 1:
                return '>'
            elif key < 1:
                return '<'
    """

    # do some check.
    if len(li) == 0 or matcher(li[0]) == '>' or matcher(li[-1]) == '<':
        return None

    # do real work.
    def _binary_search(li, matcher, lo, hi):
        mi = lo + (hi - lo) // 2
        ret = matcher(li[mi])
 
        if hi == lo:
            if ret == '=':
                return mi
            else:
                return None
 
        if ret == '=':
            ret = _binary_search(li, matcher, lo, mi)
            if ret != None:
                return ret
 
            return mi
 
        elif ret == '>':
            return _binary_search(li, matcher, lo, mi)
 
        elif ret == '<':
            return _binary_search(li, matcher, mi + 1, hi)
 
        else:
            print("matcher function returned unknown value")
            return None

    return _binary_search(li, matcher, 0, len(li) - 1)

if __name__ == "__main__":
    cb_header = """
import utils
li = [ i for i in range(1, 1000000) ]
def matcher(key):
    if key == 999999:
        return '='
    if key < 999999:
        return '<'
    if key > 999999:
        return '>'
    """

    cb_body = "utils.binary_search(li, matcher)"

    import timeit

    timer = timeit.Timer(cb_body, cb_header)
    print(timer.timeit(1))

