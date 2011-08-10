if v:version < 703
    echomsg "Error: Required vim version >= 7.3"
    finish
end

if !has('python3')
    echomsg "Error: Required vim compiled with python3"
    finish
endif

if !executable('ctags')
    echomsg "Error: Required ctags"
    finish
endif

if exists("loaded_c_complete")
    finish
endif
let loaded_c_complete = 1

py3 << eof
import os
path = os.path.dirname(vim.eval("expand('<sfile>')"))

import sys
sys.path.append(path)

from c_complete import *
eof

function! CComplete(findstart, base)
    if a:findstart
        py3 << eof
start, completion = find_completion_start()
vim.command("let s:Completion = '" + completion + "'")
vim.command("return " + str(start))
eof
    else
        py3 << eof
completion = vim.eval("s:Completion")
base = vim.eval("a:base")
matches = find_completion_matches(completion, base)

res_str = '['
for m in matches:
    res_str += "{"
    res_str += "'word':'" + m['name'].rpartition("::")[2] + "',"

    if 'kind' in m:
        res_str += "'kind':'" + m['kind'] + "',"
    else:
        res_str += "'kind':'" + 'l' + "',"

    if 'signature' in m:
        res_str += "'menu':'" + m['signature'] + "',"
    elif 'typeref' in m:
        res_str += "'menu':'" + m['typeref'] + "',"

    res_str += "},"
res_str += ']'

vim.command("return " + res_str)
eof
    endif
endfunc

function! s:vim_enter_callback()
    for f in argv()
        py3 update_file(vim.eval('f'))
    endfor
endfunc

function! s:buf_add_callback()
    py3 update_file(vim.eval('expand("<afile>")'))
endfunc

function! s:file_type_callback()
    setlocal omnifunc=CComplete
endfunc

function! s:buf_write_callback()
    py3 update_file(vim.eval('expand("<afile>")'))
endfunc

function! s:buf_delete_callback()
    py3 remove_file(vim.eval('expand("<afile>")'))
endfunc

function! SetIncludeList(...)
    let inclist = []
    for pat in a:000
        for incpath in split(glob(pat), "\n")
            if isdirectory(incpath)
                call add(inclist, incpath)
            endif
        endfor
    endfor

    py3 set_include_list(vim.eval('inclist'))
endfunc

aug C_COMPLETE
    au VimEnter *.[ch] call s:vim_enter_callback()
    au BufAdd *.[ch] call s:buf_add_callback()
    au FileType c,cpp call s:file_type_callback()
    au BufWritePost *.[ch] call s:buf_write_callback()
    au BufDelete *.[ch] call s:buf_delete_callback()
aug END

if !exists(":SetIncludeList")
    command -nargs=* -complete=dir SetIncludeList :call SetIncludeList(<f-args>)
endif

