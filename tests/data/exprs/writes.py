# !(ls >> x.py)
__xonsh__.subproc_captured_object('ls', '>>', 'x.py')

# !(ls | grep wakka > x.py)
__xonsh__.subproc_captured_object('ls', '|', 'grep', 'wakka', '>', 'x.py')

# !(ls | grep wakka >> x.py)
__xonsh__.subproc_captured_object('ls', '|', 'grep', 'wakka', '>>', 'x.py')

# !(emacs ugggh &)
__xonsh__.subproc_captured_object('emacs', 'ugggh', '&')

# !(emacs ugggh&)
__xonsh__.subproc_captured_object('emacs', 'ugggh&')

# $(ls | grep wakka)
__xonsh__.subproc_captured('ls', '|', 'grep', 'wakka')

# $(ls | grep wakka | grep jawaka)
__xonsh__.subproc_captured('ls', '|', 'grep', 'wakka', '|', 'grep', 'jawaka')

# ![ls me] and ![grep wakka]
__xonsh__.subproc_captured_hiddenobject('ls', 'me', 'and', 'grep', 'wakka')

# ![ls] and ![grep wakka] and ![grep jawaka]
__xonsh__.subproc_captured_hiddenobject('ls', 'and', 'grep', 'wakka', 'and', 'grep', 'jawaka')

# ![ls] && ![grep wakka]
__xonsh__.subproc_captured_hiddenobject('ls', '&&', 'grep', 'wakka')

# ![ls] && ![grep wakka] && ![grep jawaka]
__xonsh__.subproc_captured_hiddenobject('ls', '&&', 'grep', 'wakka', '&&', 'grep', 'jawaka')

# ![ls] or ![grep wakka]
__xonsh__.subproc_captured_hiddenobject('ls', 'or', 'grep', 'wakka')

# ![ls] or ![grep wakka] or ![grep jawaka]
__xonsh__.subproc_captured_hiddenobject('ls', 'or', 'grep', 'wakka', 'or', 'grep', 'jawaka')

# ![ls] || ![grep wakka]
__xonsh__.subproc_captured_hiddenobject('ls', '||', 'grep', 'wakka')

# ![ls] || ![grep wakka] || ![grep jawaka]
__xonsh__.subproc_captured_hiddenobject('ls', '||', 'grep', 'wakka', '||', 'grep', 'jawaka')

# $(ls > x.py)
__xonsh__.subproc_captured('ls', '>', 'x.py')

# $(ls >> x.py)
__xonsh__.subproc_captured('ls', '>>', 'x.py')

# $(ls | grep wakka > x.py)
__xonsh__.subproc_captured('ls', '|', 'grep', 'wakka', '>', 'x.py')

# $(ls | grep wakka >> x.py)
__xonsh__.subproc_captured('ls', '|', 'grep', 'wakka', '>>', 'x.py')

# $(emacs ugggh &)
__xonsh__.subproc_captured('emacs', 'ugggh', '&')

# $(emacs ugggh&)
__xonsh__.subproc_captured('emacs', 'ugggh&')
