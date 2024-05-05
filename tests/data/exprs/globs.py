# $(ls `#[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.regexsearch('#[Ff]+i*LE' , '-l'))

# $(ls r`[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.regexsearch('[Ff]+i*LE', False, False), '-l')

# $(ls r`#[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.regexsearch('#[Ff]+i*LE', False, False), '-l')

# $(ls g`[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.pathsearch(__xonsh__.globsearch, '[Ff]+i*LE', False, False), '-l')

# $(ls g`#[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.pathsearch(__xonsh__.globsearch, '#[Ff]+i*LE', False, False), '-l')

# $(ls @foo`[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.pathsearch(foo, '[Ff]+i*LE', False, False), '-l')

# print(@foo`.*`)
print(__xonsh__.pathsearch(foo, '.*', True, False))

# $(ls @foo`#[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.pathsearch(foo, '#[Ff]+i*LE', False, False), '-l')

# print(`#.*`)
print(__xonsh__.regexsearch(r'#.*', True, False))

# $(ls `[Ff]+i*LE` -l)
__xonsh__.subproc_captured('ls', *__xonsh__.regexsearch('[Ff]+i*LE', False, False), '-l')
