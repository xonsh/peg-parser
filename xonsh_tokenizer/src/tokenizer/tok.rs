use std::fmt::Debug;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Token {
    ENDMARKER,
    NAME,
    NUMBER,
    STRING,
    NEWLINE,
    INDENT,
    DEDENT,
    OP,
    FstringStart,
    FstringMiddle,
    FstringEnd,
    ErrorToken,
    Comment,
    NL,
    // xonsh specific tokens
    SearchPath,
    WS,
    MacroParam,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TokInfo {
    pub typ: Token,
    pub string: String,
    pub start: (usize, usize),
    pub end: (usize, usize),
    pub line: String,
}

impl TokInfo {
    pub fn new(
        typ: Token,
        string: String,
        start: (usize, usize),
        end: (usize, usize),
        line: String,
    ) -> Self {
        Self {
            typ,
            string,
            start,
            end,
            line,
        }
    }
}
