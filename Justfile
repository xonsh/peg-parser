set dotenv-load := true

generate:
    python3 peg_parser/tasks/generate_parser.py

profile:
    python peg_parser/tasks/profile_mem.py | tee "logs/xonsh-parser-$(date "+%Y%m%d-%H%M%S").log"

ply-add:
    git subtree add --prefix=ply --squash https://github.com/dabeaz/ply.git master

test:
    pytest peg_parser/tests

watch:
    watchexec -e py,gram --watch peg_parser/parser -- just generate

pegen-add:
    # add remote if not exists
    git remote | grep cpython || git remote add cpython https://github.com/python/cpython.git
    git fetch cpython main:cpython-main --no-tags --depth 1
    git read-tree --prefix=pegen -u cpython-main:Tools/peg_generator/pegen

we-pegen-add:
    # add remote if not exists
    git fetch https://github.com/we-like-parsers/pegen.git main:pegen-main --no-tags --depth 1
    git read-tree --prefix=pegen -u pegen-main:src/pegen

pegen-update:
    ## In future, you can merge in additional changes as follows: - https://stackoverflow.com/questions/23937436/add-subdirectory-of-remote-repo-with-git-subtree
    git checkout gitgit/master
    #$ git subtree split -P contrib/completion -b temporary-split-branch
    #$ git checkout master
    #$ git subtree merge --squash -P third_party/git-completion temporary-split-branch
    ## Now fix any conflicts if you'd modified third_party/git-completion.
    #$ git branch -D temporary-split-branch
