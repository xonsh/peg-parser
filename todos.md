- [ ] envs inside commands

```text
# ![$FOO='foo' $BAR=2 echo r'$BAR']     # xfail
__xonsh__.subproc_captured_hiddenobject('$FOO=foo', '$BAR=2', 'echo', "r'$BAR'")
```

- [ ] handling of pathsearch is different.
  It needs update from xonsh side. where it expands or passes in pymode based on the command function.

