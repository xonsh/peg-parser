use pyo3::prelude::*;

use std::hash::Hasher;
use std::hash::{DefaultHasher, Hash};

// import the macros needed
use strum_macros;

#[pyclass(
    frozen,
    rename_all = "SCREAMING_SNAKE_CASE",
    module = "xonsh_tokenizer"
)]
#[derive(Debug, Hash, PartialEq, Eq, strum_macros::Display)]
pub enum Token {
    ENDMARKER,
    NAME,
    NUMBER,
    STRING,
    NEWLINE,
    INDENT,
    DEDENT,
    OP,
    AWAIT,
    ASYNC,

    TypeIgnore,
    TypeComment,
    SoftKeyword,
    FstringStart,
    FstringMiddle,
    FstringEnd,
    ERRORTOKEN,
    COMMENT,
    NL,
    ENCODING,
    // xonsh specific tokens
    SearchPath,
    MacroParam,
    WS,
}

#[pymethods]
impl Token {
    fn is_ws(&self) -> bool {
        match self {
            Token::ENDMARKER => true,
            Token::NEWLINE => true,
            Token::INDENT => true,
            Token::DEDENT => true,
            _ => false,
        }
    }

    fn __hash__(&self) -> u64 {
        let mut hasher = DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }
}
