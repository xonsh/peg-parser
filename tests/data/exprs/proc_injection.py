# $[@$(which python)]
__xonsh__.subproc_uncaptured([*__xonsh__.subproc_captured_inject(['which', 'python'])])

# $[ls @$(dirname @$(which python))]
__xonsh__.subproc_uncaptured([*__xonsh__.subproc_captured_inject([*__xonsh__.subproc_captured_inject(['which', 'python']), 'dirname']), 'ls'])
