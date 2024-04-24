set dotenv-load := true

generate:
    python3 peg_parser/tasks/generate_parser.py

profile:
    python peg_parser/tasks/profile_mem.py | tee "logs/xonsh-parser-$(date "+%Y%m%d-%H%M%S").log"

ply-add:
    git subtree add --prefix=ply --squash https://github.com/dabeaz/ply.git master
