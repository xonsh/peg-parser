from winnow_parser import tokenize

tokens = tokenize("x = 1\n")
for t in tokens:
    print(t)
