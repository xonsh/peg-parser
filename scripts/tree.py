import subprocess as sp


def main(repo: str, path: str, dest: str, branch: str = "main"):
    """Add a folder/file from a repo using sub-tree"""
    current_branch = (
        sp.check_output("git branch --show-current", shell=True).decode().strip()
    )
    sp.check_call(
        f"git remote add tmp {repo} && git fetch tmp && git branch tmp tmp/{branch}",
        shell=True,
    )
    sp.check_call("git checkout tmp", shell=True)
    sp.check_call(f"git subtree split --prefix {path} -b tmptree", shell=True)
    sp.check_call(f"git checkout {current_branch}", shell=True)

    sp.check_call(f"git subtree add --prefix={dest} tmptree", shell=True)


def clean():
    sp.call("git branch -D tmp tmptree", shell=True)
    sp.call("git remote remove tmp", shell=True)


if __name__ == "__main__":
    try:
        main(
            repo="https://github.com/RustPython/RustPython.git",
            path="compiler/parser",
            dest="rust_parser",
        )
    finally:
        clean()
