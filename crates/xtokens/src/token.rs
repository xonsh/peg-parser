use pyo3::{pyclass, pymethods};

/// reusable token definitions that are used in multiple parsers/tokenizers

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[allow(non_camel_case_types)]
pub enum Token {
    ENDMARKER,
    NAME,
    NUMBER,
    STRING,
    NEWLINE,
    INDENT,
    DEDENT,
    OP,
    FSTRING_START,
    FSTRING_MIDDLE,
    FSTRING_END,
    ERRORTOKEN,
    COMMENT,
    NL,
    AWAIT,
    ASYNC,
    TYPE_IGNORE,
    TYPE_COMMENT,
    SOFT_KEYWORD,
    ENCODING,
    // xonsh specific tokens
    SEARCH_PATH,
    WS,
    MACRO_PARAM,
}

#[pymethods]
impl Token {
    #[getter]
    fn name(&self) -> &'static str {
        match self {
            Token::ENDMARKER => "ENDMARKER",
            Token::NAME => "NAME",
            Token::NUMBER => "NUMBER",
            Token::STRING => "STRING",
            Token::NEWLINE => "NEWLINE",
            Token::INDENT => "INDENT",
            Token::DEDENT => "DEDENT",
            Token::OP => "OP",
            Token::FSTRING_START => "FSTRING_START",
            Token::FSTRING_MIDDLE => "FSTRING_MIDDLE",
            Token::FSTRING_END => "FSTRING_END",
            Token::ERRORTOKEN => "ERRORTOKEN",
            Token::COMMENT => "COMMENT",
            Token::NL => "NL",
            Token::AWAIT => "AWAIT",
            Token::ASYNC => "ASYNC",
            Token::TYPE_IGNORE => "TYPE_IGNORE",
            Token::TYPE_COMMENT => "TYPE_COMMENT",
            Token::SOFT_KEYWORD => "SOFT_KEYWORD",
            Token::ENCODING => "ENCODING",
            Token::SEARCH_PATH => "SEARCH_PATH",
            Token::WS => "WS",
            Token::MACRO_PARAM => "MACRO_PARAM",
        }
    }
}
