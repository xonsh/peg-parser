- [ ] envs inside commands

```text
# ![$FOO='foo' $BAR=2 echo r'$BAR']     # xfail
__xonsh__.subproc_captured_hiddenobject('$FOO=foo', '$BAR=2', 'echo', "r'$BAR'")
```
