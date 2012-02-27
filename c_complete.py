#!/usr/bin/env python

import re
import vim

from ctags_cache import CtagsCache

__all__ = [
    'add_files',
    'update_files',
    'remove_files', 
    'set_include_list',
    'find_completion_start',
    'find_completion_matches',
]

COMPLETION_RE_OBJ = re.compile(r"(?:\w+\s*(?:\[.*\])*\s*(?:\.|->)\s*)*(\w*)$")

COMPLETION_COMPONENT_RE_OBJ = re.compile(r"(\w+)\s*(?:\[.*\])*\s*(?:\.|->)\s*")

FUNCTION_RE_OBJ = re.compile(r"""(?:static\s+)?
                                 (?:inline\s+)?
                                 (?:const\s+)?
                                 (?:(?:(?:struct|union|enum)\s+)|
                                    (?:\w+\s+)*)?
                                 \w+
                                 [\s\*]+(?:const\s+)?\w+\s*       # function name
                                 \((.*)\)""",
                             re.X|re.S)

ARGUMENT_RE_OBJ = re.compile(r"""(?:const\s+)?
                                 (?:(?:(struct|union|enum)\s+)|
                                    (?:\w+\s+)*)?
                                 (\w+)
                                 [\s\*]+(?:const\s+)?(\w+)\s*""", # argument name
                             re.X|re.S)

VARIABLE_RE_OBJ = re.compile(r"""(?:static\s+)?
                                 (?:const\s+)?
                                 (?:(?:(struct|union|enum)\s+)|
                                    (?:\w+\s+)*)?
                                 (\w+)
                                 ([\s\*]+(?:const\s+)?\w+\s*      # variable name
                                  (?:\[.*\]\s*)*                  # is it an array?
                                  (?:=[^;]*)?                     # may have initial value.
                                  (?:,                            # multiply variables definition.
                                     [\s\*]*(?:const\s+)?\w+\s*
                                     (?:\[.*\]\s*)*
                                     (?:=[^;]*)?)*)
                                 ;""",
                             re.X|re.S)

C_TYPES = [ 'char', 'short', 'int', 'long', 'double', 'float' ]

CTAGS_CACHE = CtagsCache('c')

def add_files(files):
    CTAGS_CACHE.add_files(files)

def update_files(files):
    CTAGS_CACHE.update_files(files)

def remove_files(files):
    CTAGS_CACHE.remove_files(files)

def set_include_list(inclist):
    global CTAGS_CACHE
    CTAGS_CACHE = CtagsCache('c', inclist)

    files = []
    for b in vim.buffers:
        if not b.name:
            continue

        if not b.name.endswith('.c') and not b.name.endswith('.h'):
            continue

        if not int(vim.eval("buflisted('" + b.name + "')")):
            continue

        files.append(b.name)

    CTAGS_CACHE.add_files(files)

def find_completion_start():
    row, col = vim.current.window.cursor

    # the pattern matches string like this: 'abc[10].def->ghi', 'abc',
    # etc.
    match = COMPLETION_RE_OBJ.search(vim.current.line[0:col])

    return match.start(1), match.group(0)

def line_is_end(line):
    line = re.sub(r'/\*.*\*/\s*$', '', line)
    line = re.sub(r'//.*$', '', line)
    line = line.rstrip()

    if len(line) == 0:
        return 0
    elif line[-1] in ';{}':
        return 1
    else:
        return 0

def line_indent_level(line):
    tab_stop = int(vim.eval("&tabstop"))
    shift_width = int(vim.eval("&shiftwidth"))
    prefix_space = 0
    for i in range(0, len(line)):
        if line[i] == ' ':
            prefix_space += 1
        elif line[i] == '\t':
            prefix_space += tab_stop
        else:
            break

    return prefix_space // shift_width

def split_var_names(s):
    s = re.sub(r"'(?:.|\\.)'", '', s)
    s = re.sub(r'\\.', '', s)
    s = re.sub(r'"[^"]*"', '', s)

    for p in [r'\{[^\{]*\}', r'\([^\(]*\)', r'\[[^\[]*\]']:
        while 1:
            t = re.sub(p, '', s)
            if s != t:
                s = t
            else:
                break

    s = re.sub(r'=[^,]*', '', s)
    s = re.sub(r'[\s\*]', '', s)

    return s.split(',')

def var_names(statements):
    it = VARIABLE_RE_OBJ.finditer(statements)
    for st in it:
        typename = ''
        if st.group(1):
            typename = st.group(1) + ':' + st.group(2)
        elif st.group(2) not in C_TYPES:
            typename = st.group(2)

        for var in split_var_names(st.group(3)):
            if typename:
                yield {'name': var, 'typeref': typename}
            else:
                yield {'name': var}

def arg_names(st):
    it = ARGUMENT_RE_OBJ.finditer(st)
    for arg in it:
        tag = {'name': arg.group(3)}
        if arg.group(1):
            tag['typeref'] = arg.group(1) + ':' + arg.group(2)
        elif arg.group(2) not in C_TYPES:
            tag['typeref'] = arg.group(2)
            
        yield tag

def get_local_vars(name_prefix, match_whole = 0):
    if not match_whole:
        matcher = lambda x: x.startswith(name_prefix)
    else:
        matcher = lambda x: x == name_prefix

    origin_row, origin_col = vim.current.window.cursor

    res = []
    while 1:
        end_row, end_col = vim.current.window.cursor
        vim.eval("searchpair('{', '', '}', 'bW', '')")
        start_row, start_col = vim.current.window.cursor
        if start_col == end_col and start_row == end_row:
            break

        # the row of vim window cursor is start from 1, col is start
        # from 0.  but, we assume symbol '{' and '}' always at the end
        # of previous scope.
        if start_row == end_row:
            scope = [vim.current.buffer[start_row]]
        else:
            scope = vim.current.buffer[start_row:end_row]

        scope[-1] = scope[-1][:end_col]

        # the indent level of scope is decided by the line which include
        # '{'.  indent level of this line plus 1 is scope indent level.
        scope_ind_lev = line_indent_level(vim.current.buffer[start_row - 1]) + 1

        statements = ''
        for line in scope:
            statements += line;

            if line_is_end(line):
                # now we got a complete statements.
                st_ind_lev = line_indent_level(statements)
                if scope_ind_lev >= st_ind_lev:
                    for var in var_names(statements):
                        if matcher(var['name']) and var not in res:
                            res.append(var)

                statements = ''

        # whether in the function header. if yes, parse arguments and
        # break whole "while 1" loop.
        if scope_ind_lev == 1:
            start_row -= 1
            statements = vim.current.buffer[start_row][:start_col]
            while 1:
                func = FUNCTION_RE_OBJ.search(statements)
                if func:
                    for arg in arg_names(func.group(1)):
                        if matcher(arg['name']) and arg not in res:
                            res.append(arg)
                    break

                start_row -= 1
                if start_row >= 0 and \
                   not line_is_end(vim.current.buffer[start_row]):
                    statements = vim.current.buffer[start_row] + statements
                else:
                    break

            break

    vim.current.window.cursor = origin_row, origin_col

    return res

def find_typeref_of_typedef(typedef):
    """
    translate typedefed type to original typeref.  if original typeref
    is not struct or union, it will return string ''.
    """
    typename = ''
    while 1:
        tags = CTAGS_CACHE.find_tags(typedef, 1)
        tags = [t for t in tags 
                   if (t['kind'] == 't' and 'typeref' in t) or \
                      (t['kind'] == 'c')]
        if not tags:
            break

        tag = tags[0]
        if tag['kind'] == 'c':
            typename = tag['name']
            break
        elif tag['typeref'].startswith("struct:") or \
             tag['typeref'].startswith("union:") or \
             tag['typeref'].startswith("class:"):
            typename = tag['typeref']
            break

        typedef = tag['typeref']

    return typename

def typeref_to_struct_name(typeref):
    """
    the 'typeref' field is generated by ctags, it may contain many
    middle struct name, we don't need them. but, the "__anon*" struct is
    useful, should keep it.
    """
    kind, sep, name = typeref.partition(':')
    name_parts = name.split('::')
    name_parts.reverse()
    name = []
    for s in name_parts:
        name.insert(0, s)
        if not s.startswith('__anon'):
            break

    return kind + sep + "::".join(name)

def is_not_member_of_named_child_struct(tag, struct_name, struct_tags):
    kind = None
    if 'struct' in tag:
        kind = 'struct'
    elif 'union' in tag:
        kind = 'union'
    elif 'class' in tag:
        kind = 'class'

    # unlikely.
    else:
        return 0
    
    # tag is member of struct.
    if tag[kind] == struct_name:
        return 1

    for t2 in struct_tags:
        if tag == t2 or 'typeref' not in t2:
            continue

        # the parent struct found, tag is not member of struct.
        if kind + ':' + tag[kind] == typeref_to_struct_name(t2['typeref']):
            return 0

    return 1

def find_completion_matches(completion, base):
    if not completion:
        return []

    elif completion != base:
        it = COMPLETION_COMPONENT_RE_OBJ.finditer(completion)
        last_struct = ''
        last_component_start = 0
        for part in it:
            tags = None
            if not last_struct:
                tags = [t for t in get_local_vars(part.group(1), 1)
                          if 'typeref' in t]
                if not tags:
                    tags = CTAGS_CACHE.find_tags(part.group(1), 1)
                    tags = [t for t in tags
                              if t['kind'] == 'v' and 'typeref' in t]
            else:
                if last_struct.startswith("struct:") or \
                   last_struct.startswith("union:") or \
                   last_struct.startswith("class:"):
                       kind, sep, name = last_struct.partition(':')
                else:
                    name = last_struct

                tags = CTAGS_CACHE.find_tags(name + '::')
                tags = [t for t in tags \
                          if t['kind'] in 'fmpt' and \
                             'typeref' in t and \
                             t['name'].rpartition('::')[2] == part.group(1) and \
                             is_not_member_of_named_child_struct(t, name, tags)]

            # no tags found, stop.
            if not tags:
                return []

            # if there are more than one tags, just use the first one.
            t = tags[0]
            if t['typeref'].startswith("struct:") or \
               t['typeref'].startswith("union:") or \
               t['typeref'].startswith("class:"):
                typeref = t['typeref']
            else:
                typeref = find_typeref_of_typedef(t['typeref'])
                # if typeref can not convert to a struct or union, stop.
                if not typeref:
                    return []

            last_struct = typeref_to_struct_name(typeref)
            last_component_start = part.end(0)

        last_component = completion[last_component_start:]

        if last_struct.startswith("struct:") or \
           last_struct.startswith("union:") or \
           last_struct.startswith("class:"):
               kind, sep, name = last_struct.partition(':')
        else:
            name = last_struct

        tags = CTAGS_CACHE.find_tags(name + '::')
        tags = [t for t in tags \
                  if t['kind'] in 'fmpt' and \
                     t['name'].rpartition('::')[2].startswith(last_component) and \
                     is_not_member_of_named_child_struct(t, name, tags)]

        return tags

    else:
        lvars = get_local_vars(base)
        gsyms = CTAGS_CACHE.find_tags(base)
        gsyms = [s for s in gsyms \
                   if s['kind'] in 'cdefgntspuv' and \
                      not (s['kind'] in 'pft' and \
                           ('struct' in s or 'union' in s or 'class' in s))]

        return lvars + gsyms

