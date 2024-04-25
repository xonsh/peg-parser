# $(cmd sub-cmd --opt)
__xonsh__.subproc_captured_stdout('cmd sub-cmd --opt')

# $[cmd sub-cmd --opt]
__xonsh__.subproc_uncaptured('cmd sub-cmd --opt')

# ![cmd sub-cmd --opt]
__xonsh__.subproc_uncaptured_object('cmd sub-cmd --opt')

# !(cmd sub-cmd --opt)
__xonsh__.subproc_captured_object('cmd sub-cmd --opt')
