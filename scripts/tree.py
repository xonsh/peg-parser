import sys


def main():
    """Add a folder/file from a repo using sub-tree"""
    "git remote add tmp https://github.com/RustPython/RustPython.git"
    "git fetch tmp"
    "git branch tmp tmp/main"
    "git checkout tmp"
    "git subtree split --prefix native -b tmptree"
    "git checkout main"

    "git subtree add --prefix=src tmptree"

    "git branch -D tmp tmptree"
    "git remote remove tmp"

    print(sys.argv)

