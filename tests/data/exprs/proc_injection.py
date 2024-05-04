# $[@$(which python)]
__xonsh__.subproc_uncaptured([*__xonsh__.subproc_captured_inject(['which', 'python'])])

# $[ls @$(dirname @$(which python))]
__xonsh__.subproc_uncaptured(['ls', *__xonsh__.subproc_captured_inject(['dirname', *__xonsh__.subproc_captured_inject(['which', 'python'])])])
