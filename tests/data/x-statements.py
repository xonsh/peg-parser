## range tuple
*range(4),

## range tuple 4
*range(4,), 4

## star eq
*y, = [1, 2, 3]

## function_blank_line
def foo():
    ascii_art = [
        "(╯°□°）╯︵ ┻━┻",
        "¯\\_(ツ)_/¯",
        "┻━┻︵ \\(°□°)/ ︵ ┻━┻",
    ]
    import random
    i = random.randint(0,len(ascii_art)) - 1
    print("    Get to work!")
    print(ascii_art[i])

## async_func
async def bar():
    pass


## async decorator
@g
async def f():
    pass

## async await
async def f():
    await g

## match
match = 1
case = 2
def match():
    pass
class case():
    pass

## nested functions
def f():
    def g():
        return 1
    return g
