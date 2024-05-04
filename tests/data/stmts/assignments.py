# $WAKKA
__xonsh__.env['WAKKA']

# $y = 'one'
__xonsh__.env['y'] = 'one'

# $WAKKA = 42
__xonsh__.env['WAKKA'] = 42

# y = $x
y = __xonsh__.env['x']

# y = ${x}
y = __xonsh__.env[str(x)]

# y = ${'x' + 'y'}
y = __xonsh__.env[str('x' + 'y')]

# ${None or "WAKKA"}
__xonsh__.env[str(None or 'WAKKA')]

# ${$JAWAKA}
__xonsh__.env[str(__xonsh__.env['JAWAKA'])]

# $WAKKA = 42
__xonsh__

# ${${"JAWA" + $JAWAKA[-2:]}}
__xonsh__
