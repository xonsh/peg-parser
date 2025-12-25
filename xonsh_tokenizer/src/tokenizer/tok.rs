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
    pub span: (usize, usize),
    pub start: (usize, usize),
    pub end: (usize, usize),
}

impl TokInfo {
    pub fn new(
        typ: Token,
        span: (usize, usize),
        start: (usize, usize),
        end: (usize, usize),
    ) -> Self {
        Self {
            typ,
            span,
            start,
            end,
        }
    }

    pub fn get_string<'a>(&self, source: &'a str) -> &'a str {
        &source[self.span.0..self.span.1]
    }
}
