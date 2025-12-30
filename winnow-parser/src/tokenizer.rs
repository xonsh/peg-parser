use pyo3::prelude::*;
use pyo3::types::PyString;
use winnow::ascii::{digit1, hex_digit1, line_ending};
use winnow::combinator::{alt, dispatch, opt, peek, repeat};

use winnow::error::ErrMode;
use winnow::prelude::*;
use winnow::stream::Stateful;
use winnow::token::{any, take_until, take_while};

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

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FStringState {
    pub quote: Vec<u8>,
    pub brace_level: usize,
    pub in_format_spec: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LexerState {
    pub indents: Vec<usize>,
    pub fstring_stack: Vec<FStringState>,
    pub paren_level: usize,
    pub at_beginning_of_line: bool,
    pub has_content: bool,
}

impl Default for LexerState {
    fn default() -> Self {
        Self {
            indents: vec![0],
            fstring_stack: Vec::new(),
            paren_level: 0,
            at_beginning_of_line: true,
            has_content: false,
        }
    }
}

pub type Stream<'s> = Stateful<&'s [u8], LexerState>;

#[pyclass]
#[derive(Debug)]
pub struct TokInfo {
    #[pyo3(get)]
    #[pyo3(name = "type")]
    pub typ: Token,
    #[pyo3(get)]
    pub span: (usize, usize),
    #[pyo3(get)]
    pub start: (usize, usize),
    #[pyo3(get)]
    pub end: (usize, usize),
    pub source: Py<PyString>,
}

#[pymethods]
impl TokInfo {
    #[new]
    pub fn new(
        typ: Token,
        span: (usize, usize),
        start: (usize, usize),
        end: (usize, usize),
        source: Py<PyString>,
    ) -> Self {
        Self {
            typ,
            span,
            start,
            end,
            source,
        }
    }

    #[getter]
    pub fn string(&self, py: Python<'_>) -> String {
        let s = self.source.bind(py).to_str().unwrap();
        s[self.span.0..self.span.1].to_string()
    }

    #[allow(deprecated)]
    pub fn is_exact_type(&self, _py: Python<'_>, typ: String) -> bool {
        self.typ == Token::OP && Python::with_gil(|py| self.string(py) == typ)
    }

    pub fn loc_start(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = std::collections::HashMap::new();
        map.insert("lineno", self.start.0);
        map.insert("col_offset", self.start.1);
        map
    }

    pub fn loc_end(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = std::collections::HashMap::new();
        map.insert("end_lineno", self.end.0);
        map.insert("end_col_offset", self.end.1);
        map
    }

    pub fn loc(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = self.loc_start();
        map.insert("end_lineno", self.end.0);
        map.insert("end_col_offset", self.end.1);
        map
    }

    #[allow(deprecated)]
    fn __repr__(&self) -> String {
        Python::with_gil(|py| {
            let s = self.source.bind(py).to_str().unwrap();
            let string_val = &s[self.span.0..self.span.1];
            format!(
                "TokInfo(type={:?}, string={:?}, start={:?}, end={:?})",
                self.typ, string_val, self.start, self.end
            )
        })
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

impl Clone for TokInfo {
    fn clone(&self) -> Self {
        #[allow(deprecated)]
        Python::with_gil(|py| Self {
            typ: self.typ,
            span: self.span,
            start: self.start,
            end: self.end,
            source: self.source.clone_ref(py),
        })
    }
}

impl PartialEq for TokInfo {
    fn eq(&self, other: &Self) -> bool {
        self.typ == other.typ
            && self.span == other.span
            && self.start == other.start
            && self.end == other.end
            && Python::with_gil(|py| {
                self.source.bind(py).to_str().unwrap() == other.source.bind(py).to_str().unwrap()
            })
    }
}

// ... helper parsers ...
pub fn oct_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    (
        take_while(1.., b'0'..=b'7'),
        repeat(0.., (b"_", take_while(1.., b'0'..=b'7'))).map(|_: ()| ()),
    )
        .take()
        .parse_next(input)
}

pub fn bin_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    (
        take_while(1.., b'0'..=b'1'),
        repeat(0.., (b"_", take_while(1.., b'0'..=b'1'))).map(|_: ()| ()),
    )
        .take()
        .parse_next(input)
}

pub fn hex_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    (hex_digit1, repeat(0.., (b"_", hex_digit1)).map(|_: ()| ()))
        .take()
        .parse_next(input)
}

pub fn digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    (digit1, repeat(0.., (b"_", digit1)).map(|_: ()| ()))
        .take()
        .parse_next(input)
}

pub fn parse_ws<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    take_while(1.., (b' ', b'\t', 0x0c)).parse_next(input)
}

pub fn parse_comment<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    (b"#", take_while(0.., |c| c != b'\r' && c != b'\n'))
        .take()
        .parse_next(input)
}

pub fn parse_name<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    let res = take_while(1.., |c: u8| {
        c.is_ascii_alphanumeric() || c == b'_' || c > 127
    })
    .verify(|s: &[u8]| {
        let c = s[0];
        !c.is_ascii_digit()
    })
    .parse_next(input);

    if res.is_ok() {
        input.state.at_beginning_of_line = false;
    }
    res
}

pub fn parse_number<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    let res = alt((
        (alt((b"0x", b"0X")), hex_digit1_w).take(),
        (alt((b"0b", b"0B")), bin_digit1_w).take(),
        (alt((b"0o", b"0O")), oct_digit1_w).take(),
        (
            digit1_w,
            opt((b".", opt(digit1_w))),
            opt((alt((b'e', b'E')), opt(alt((b'+', b'-'))), digit1_w)),
        )
            .take(),
        (b".", digit1_w).take(),
    ))
    .parse_next(input);

    if res.is_ok() {
        input.state.at_beginning_of_line = false;
    }
    res
}

pub fn parse_op<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    let op: &[u8] = alt((
        alt((b"...", b">>=", b"<<=", b"**=", b"//=", b"??", b"||", b"&&")),
        alt((b"@$(", b"@(", b"!(", b"![", b"$(", b"$[", b"${", b"!=")),
        alt((b"%=", b"&=", b"**", b"*=", b"+=", b"-=", b"->", b"//")),
        alt((b"/=", b":=", b"<<", b"<=", b"==", b">=", b">>", b"@=")),
        alt((b"^=", b"|=", b"%", b"&", b"(", b")", b"*", b"+")),
        alt((b"> &", b">&", b"&>", b",")),
        alt((b"-", b".", b"/", b":", b";", b"<", b"=")),
        alt((b">", b"@", b"[", b"]", b"^", b"{", b"|", b"}")),
        alt((b"~", b"!", b"$", b"?")),
    ))
    .parse_next(input)?;

    let state = &mut input.state;
    state.at_beginning_of_line = false;

    if op.ends_with(b"(") || op.ends_with(b"[") || op.ends_with(b"{") {
        state.paren_level += 1;
    } else if op == b")" || op == b"]" || op == b"}" {
        state.paren_level = state.paren_level.saturating_sub(1);
    }

    let fs_len = state.fstring_stack.len();
    if let Some(f_state) = state.fstring_stack.last_mut() {
        if f_state.brace_level > 0 {
            if op.ends_with(b"{") {
                f_state.brace_level += 1;
            } else if op == b"}" {
                f_state.brace_level -= 1;
                if f_state.brace_level == 0 && f_state.in_format_spec {
                    f_state.in_format_spec = false;
                }
            } else if op == b":" && f_state.brace_level == 1 && state.paren_level == fs_len {
                f_state.in_format_spec = true;
                f_state.brace_level = 0;
            }
        }
    }

    Ok(op)
}

pub fn parse_string_prefix<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    alt((
        alt([
            b"rf", b"fr", b"rb", b"br", b"pf", b"fp", b"pr", b"rp", b"RF", b"FR", b"RB", b"BR",
            b"PF", b"FP", b"PR", b"RP", b"rF", b"Rf", b"fR", b"Fr", b"rB", b"Rb", b"bR", b"Br",
            b"pF", b"Pf", b"fP", b"Fp", b"pR", b"Rp", b"rP", b"Pr",
        ]),
        alt([b"u", b"p", b"r", b"f", b"b", b"U", b"P", b"R", b"F", b"B"]),
        b"",
    ))
    .parse_next(input)
}

pub fn parse_full_string<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    let start = input.input;
    let _ = parse_string_prefix(input)?;
    let quote_len = if input.starts_with(b"'''") || input.starts_with(b"\"\"\"") {
        3
    } else if input.starts_with(b"\'") || input.starts_with(b"\"") {
        1
    } else {
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    };

    let quote = &input.input[..quote_len];
    input.input = &input.input[quote_len..];

    loop {
        if input.is_empty() {
            return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
        }
        if input.starts_with(quote) {
            input.input = &input.input[quote_len..];
            break;
        }
        if input.starts_with(b"\\") {
            let _ = any.parse_next(input)?;
            if !input.is_empty() {
                let _ = any.parse_next(input)?;
            }
        } else {
            let _ = any.parse_next(input)?;
        }
    }

    input.state.at_beginning_of_line = false;
    let consumed_len = start.len() - input.input.len();
    Ok(&start[..consumed_len])
}

pub fn parse_search_path<'s>(input: &mut Stream<'s>) -> ModalResult<&'s [u8]> {
    let res = (
        opt(alt((
            take_while(1.., (b'r', b'g', b'p', b'f')),
            (
                b"@",
                take_while(0.., |c: u8| c.is_ascii_alphanumeric() || c == b'_'),
            )
                .take(),
        ))),
        b"`",
        take_until(0.., b"`".as_slice()),
        b"`",
    )
        .take()
        .parse_next(input);

    if res.is_ok() {
        input.state.at_beginning_of_line = false;
    }
    res
}

pub fn parse_indentation<'s>(input: &mut Stream<'s>) -> ModalResult<Token> {
    if !input.state.at_beginning_of_line {
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    }

    input.state.at_beginning_of_line = false;
    let last_indent = *input.state.indents.last().unwrap();

    let mut check_empty = input.clone();
    let ws_res: Result<&[u8], ErrMode<winnow::error::ContextError>> = parse_ws(&mut check_empty);
    let (indent_len, new_input) = match ws_res {
        Ok(ws) => (ws.len(), check_empty),
        Err(_) => (0, input.clone()),
    };

    let mut check_content = new_input.clone();
    let le_res: Result<&[u8], ErrMode<winnow::error::ContextError>> =
        line_ending.parse_next(&mut check_content);
    let is_empty_line =
        le_res.is_ok() || parse_comment(&mut check_content).is_ok() || check_content.is_empty();

    if is_empty_line {
        let consumed_len = input.input.len() - new_input.input.len();
        if consumed_len > 0 {
            input.input = &input.input[consumed_len..];
            input.state.at_beginning_of_line = true;
            return Ok(Token::WS);
        } else {
            input.state.at_beginning_of_line = true;
            return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
        }
    }

    if input.state.paren_level > 0 || !input.state.fstring_stack.is_empty() {
        let consumed_len = input.input.len() - new_input.input.len();
        if consumed_len > 0 {
            input.input = &input.input[consumed_len..];
            return Ok(Token::WS);
        }
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    }

    if indent_len > last_indent {
        let consumed_len = input.input.len() - new_input.input.len();
        input.input = &input.input[consumed_len..];
        input.state.indents.push(indent_len);
        Ok(Token::INDENT)
    } else if indent_len < last_indent {
        input.state.indents.pop();
        input.state.at_beginning_of_line = true;
        Ok(Token::DEDENT)
    } else {
        let consumed_len = input.input.len() - new_input.input.len();
        if consumed_len > 0 {
            input.input = &input.input[consumed_len..];
            Ok(Token::WS)
        } else {
            Err(ErrMode::Backtrack(winnow::error::ContextError::new()))
        }
    }
}

pub fn parse_fstring_content<'s>(input: &mut Stream<'s>) -> ModalResult<Token> {
    let in_fstring_content = input
        .state
        .fstring_stack
        .last()
        .map(|s| s.brace_level == 0)
        .unwrap_or(false);

    if !in_fstring_content {
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    }

    let state_quote = input.state.fstring_stack.last().unwrap().quote.clone();
    let state_in_format_spec = input.state.fstring_stack.last().unwrap().in_format_spec;

    if input.starts_with(&state_quote) {
        let quote_len = state_quote.len();
        input.input = &input.input[quote_len..];
        input.state.fstring_stack.pop();
        return Ok(Token::FSTRING_END);
    }

    if state_in_format_spec && input.starts_with(b"}") && !input.starts_with(b"}}") {
        input.input = &input.input[1..];
        let state_mut = input.state.fstring_stack.last_mut().unwrap();
        state_mut.in_format_spec = false;
        state_mut.brace_level = 0;
        input.state.paren_level = input.state.paren_level.saturating_sub(1);
        return Ok(Token::OP);
    }

    if !state_in_format_spec && input.starts_with(b"{") {
        if !input.starts_with(b"{{") {
            input.input = &input.input[1..];
            let state_mut = input.state.fstring_stack.last_mut().unwrap();
            state_mut.brace_level = 1;
            state_mut.in_format_spec = false;
            input.state.paren_level += 1;
            return Ok(Token::OP);
        }
    }

    let mut temp_input = input.clone();
    let mut len = 0;
    while !temp_input.is_empty() {
        let curr_quote = &input.state.fstring_stack.last().unwrap().quote;

        // Handle double braces {{ and }} - they are treated as content
        if temp_input.starts_with(b"{{") || temp_input.starts_with(b"}}") {
            len += 2;
            temp_input.input = &temp_input.input[2..];
            continue;
        }

        // Break on single braces or closing quote
        if temp_input.starts_with(b"{")
            || temp_input.starts_with(b"}")
            || temp_input.starts_with(curr_quote.as_slice())
        {
            break;
        }
        // Break if in format spec & start of nested fields or end
        // (Handled above by generalized { } break)

        if temp_input.starts_with(b"\\") {
            len += 1;
            temp_input.input = &temp_input.input[1..];
            if !temp_input.is_empty() {
                let bytes = temp_input.input;
                let l = if bytes[0] < 128 {
                    1
                } else {
                    // Simple UTF-8 length determination or just take 1 if we don't care about char boundary here
                    // But we should correct len.
                    // Winnow doesn't expose utf8 length helper easily on &[u8].
                    // Let's use string conversion for safety or a small helper.
                    match std::str::from_utf8(bytes) {
                        Ok(s) => s.chars().next().map(|c| c.len_utf8()).unwrap_or(1),
                        Err(e) => e.valid_up_to().max(1), // Fallback
                    }
                };
                len += l;
                temp_input.input = &temp_input.input[l..];
            }
        } else {
            let bytes = temp_input.input;
            let l = if bytes[0] < 128 {
                1
            } else {
                match std::str::from_utf8(bytes) {
                    Ok(s) => s.chars().next().map(|c| c.len_utf8()).unwrap_or(1),
                    Err(e) => e.valid_up_to().max(1),
                }
            };
            len += l;
            temp_input.input = &temp_input.input[l..];
        }
    }

    if len > 0 {
        input.input = &input.input[len..];
        return Ok(Token::FSTRING_MIDDLE);
    }

    Err(ErrMode::Backtrack(winnow::error::ContextError::new()))
}

pub fn parse_fstring_start<'s>(input: &mut Stream<'s>) -> ModalResult<Token> {
    let mut check = input.clone();
    let prefix = parse_string_prefix(&mut check)?;

    if !prefix.to_ascii_lowercase().contains(&b'f') || check.is_empty() {
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    }

    let ql = if check.starts_with(b"'''") || check.starts_with(b"\"\"\"") {
        3
    } else if check.starts_with(b"\'") || check.starts_with(b"\"") {
        1
    } else {
        0
    };

    if ql > 0 {
        let quote = &check.input[..ql];
        input.input = &check.input[ql..];

        input.state.fstring_stack.push(FStringState {
            quote: quote.to_vec(),
            brace_level: 0,
            in_format_spec: false,
        });
        input.state.at_beginning_of_line = false;
        Ok(Token::FSTRING_START)
    } else {
        Err(ErrMode::Backtrack(winnow::error::ContextError::new()))
    }
}

pub fn parse_line_ending_token<'s>(input: &mut Stream<'s>) -> ModalResult<Token> {
    let _ = line_ending.parse_next(input)?;
    input.state.at_beginning_of_line = true;
    let res = if input.state.paren_level > 0
        || !input.state.fstring_stack.is_empty()
        || !input.state.has_content
    {
        Token::NL
    } else {
        Token::NEWLINE
    };
    input.state.has_content = false;
    Ok(res)
}

pub struct Tokenizer<'s> {
    input: Stream<'s>,
    offset: usize,
    line: usize,
    col: usize,
    pending_tokens: std::collections::VecDeque<TokInfo>,
    eof_emitted: bool,
    source_py: Py<PyString>,
}

impl<'s> Tokenizer<'s> {
    pub fn new(_py: Python<'_>, source: Py<PyString>, source_bytes: &'s [u8]) -> Self {
        Self {
            input: Stateful {
                input: source_bytes,
                state: LexerState::default(),
            },
            offset: 0,
            line: 1,
            col: 0,
            pending_tokens: std::collections::VecDeque::new(),
            eof_emitted: false,
            source_py: source,
        }
    }

    fn py(&self) -> Python<'_> {
        unsafe { Python::assume_attached() }
    }

    fn update_coords(&mut self, consumed: &[u8]) {
        let s = std::str::from_utf8(consumed).unwrap_or("");
        for c in s.chars() {
            self.offset += c.len_utf8();
            if c == '\n' {
                self.line += 1;
                self.col = 0;
            } else {
                self.col += 1;
            }
        }
    }

    pub fn next_token(&mut self) -> Option<TokInfo> {
        loop {
            if let Some(tok) = self.pending_tokens.pop_front() {
                return Some(tok);
            }

            if self.input.is_empty() {
                if !self.input.state.fstring_stack.is_empty() {
                    return None;
                }
                if self.eof_emitted {
                    return None;
                }

                if !self.input.state.at_beginning_of_line {
                    self.input.state.at_beginning_of_line = true;
                    return Some(TokInfo::new(
                        Token::NEWLINE,
                        (self.offset, self.offset),
                        (self.line, self.col),
                        (self.line, self.col),
                        self.source_py.clone_ref(self.py()),
                    ));
                }

                if self.input.state.indents.len() > 1 {
                    self.input.state.indents.pop();
                    return Some(TokInfo::new(
                        Token::DEDENT,
                        (self.offset, self.offset),
                        (self.line, 0),
                        (self.line, 0),
                        self.source_py.clone_ref(self.py()),
                    ));
                }

                self.eof_emitted = true;
                return Some(TokInfo::new(
                    Token::ENDMARKER,
                    (self.offset, self.offset),
                    (self.line, self.col),
                    (self.line, self.col),
                    self.source_py.clone_ref(self.py()),
                ));
            }

            if self.input.starts_with(b"\\") {
                let mut check = self.input.clone();
                let _: Result<u8, ErrMode<winnow::error::ContextError>> =
                    any.parse_next(&mut check);
                let mut skipped_len = 1;
                let r_ws: Result<&[u8], ErrMode<winnow::error::ContextError>> =
                    parse_ws(&mut check);
                if let Ok(ws) = r_ws {
                    skipped_len += ws.len();
                }
                let r_le: Result<&[u8], ErrMode<winnow::error::ContextError>> =
                    line_ending.parse_next(&mut check);
                if let Ok(le) = r_le {
                    skipped_len += le.len();

                    let consumed = &self.input.input[..skipped_len];
                    self.update_coords(consumed);
                    self.input.input = &self.input.input[skipped_len..];
                    continue;
                }
            }

            let start_offset = self.offset;
            let start_coords = (self.line, self.col);
            let old_input = self.input.clone();

            let result: Result<Token, ErrMode<winnow::error::ContextError>> =
                if self.input.state.at_beginning_of_line {
                    let initial_input = self.input.clone();
                    let _res = parse_indentation(&mut self.input);
                    if _res.is_ok() {
                        _res
                    } else {
                        self.input = initial_input; // Restore state (including at_beginning_of_line)

                        if !self.input.state.fstring_stack.is_empty()
                            && self
                                .input
                                .state
                                .fstring_stack
                                .last()
                                .map(|s| s.brace_level == 0)
                                .unwrap_or(false)
                        {
                            parse_fstring_content(&mut self.input)
                        } else {
                            dispatch! { peek(any);
                                b'{' => |i: &mut Stream<'_>| {
                                     if !i.state.fstring_stack.is_empty() {
                                         parse_fstring_content(i)
                                     } else {
                                         parse_op.map(|_| Token::OP).parse_next(i)
                                     }
                                },
                                b' ' | b'\t' | 0x0c => parse_ws.map(|_| Token::WS),
                                b'#' => parse_comment.map(|_| Token::COMMENT),
                                b'\n' | b'\r' => parse_line_ending_token,
                                b'0'..=b'9' => parse_number.map(|_| Token::NUMBER),
                                b'a'..=b'z' | b'A'..=b'Z' | b'_' | b'\x80'..=b'\xff' => alt((
                                    parse_fstring_start,
                                    // identifiers can start search path?
                                    parse_search_path.map(|_| Token::SEARCH_PATH),
                                    parse_full_string.map(|_| Token::STRING),
                                    parse_name.map(|_| Token::NAME)
                                )),
                                b'\'' | b'"' => alt((
                                     parse_fstring_start,
                                     parse_full_string.map(|_| Token::STRING)
                                )),
                                b'`' => parse_search_path.map(|_| Token::SEARCH_PATH),
                                b'@' => alt((
                                    parse_search_path.map(|_| Token::SEARCH_PATH),
                                    parse_op.map(|_| Token::OP)
                                )),
                                b'.' => alt((
                                    parse_number.map(|_| Token::NUMBER),
                                    parse_op.map(|_| Token::OP)
                                )),
                                _ => alt((
                                    parse_op.map(|_| Token::OP),
                                    any.map(|_| Token::ERRORTOKEN)
                                ))
                            }
                            .parse_next(&mut self.input)
                        }
                    }
                } else if !self.input.state.fstring_stack.is_empty()
                    && self
                        .input
                        .state
                        .fstring_stack
                        .last()
                        .map(|s| s.brace_level == 0)
                        .unwrap_or(false)
                {
                    parse_fstring_content(&mut self.input)
                } else {
                    dispatch! { peek(any);
                            b'{' => |i: &mut Stream<'_>| {
                                 if !i.state.fstring_stack.is_empty() {
                                     parse_fstring_content(i)
                                 } else {
                                     parse_op.map(|_| Token::OP).parse_next(i)
                                 }
                            },
                            b' ' | b'\t' | 0x0c => parse_ws.map(|_| Token::WS),
                            b'#' => parse_comment.map(|_| Token::COMMENT),
                            b'\n' | b'\r' => parse_line_ending_token,
                            b'0'..=b'9' => parse_number.map(|_| Token::NUMBER),
                            b'a'..=b'z' | b'A'..=b'Z' | b'_' | b'\x80'..=b'\xff' => alt((
                                parse_fstring_start,
                                parse_search_path.map(|_| Token::SEARCH_PATH),
                                parse_full_string.map(|_| Token::STRING),
                                parse_name.map(|_| Token::NAME)
                            )),
                            b'\'' | b'"' => alt((
                                 parse_fstring_start,
                                 parse_full_string.map(|_| Token::STRING)
                            )),
                        b'`' => parse_search_path.map(|_| Token::SEARCH_PATH),
                        b'@' => alt((
                            parse_search_path.map(|_| Token::SEARCH_PATH),
                            parse_op.map(|_| Token::OP)
                        )),
                        b'.' => alt((
                            parse_number.map(|_| Token::NUMBER),
                            parse_op.map(|_| Token::OP)
                        )),
                        _ => alt((
                            parse_op.map(|_| Token::OP),
                            any.map(|_| Token::ERRORTOKEN)
                        ))
                    }
                    .parse_next(&mut self.input)
                };

            let consumed_len = old_input.input.len() - self.input.input.len();
            let consumed = &old_input.input[..consumed_len];

            self.update_coords(consumed);

            match result {
                Ok(tok) => {
                    match tok {
                        Token::NAME
                        | Token::NUMBER
                        | Token::STRING
                        | Token::OP
                        | Token::FSTRING_START
                        | Token::FSTRING_MIDDLE
                        | Token::SEARCH_PATH
                        | Token::AWAIT
                        | Token::ASYNC
                        | Token::SOFT_KEYWORD
                        | Token::MACRO_PARAM => {
                            self.input.state.has_content = true;
                        }
                        _ => {}
                    }
                    return Some(TokInfo::new(
                        tok,
                        (start_offset, self.offset),
                        start_coords,
                        (self.line, self.col),
                        self.source_py.clone_ref(self.py()),
                    ));
                }
                Err(_) => {
                    if self.offset == start_offset && !self.input.is_empty() {
                        let mut it = self.input.input;
                        let l = if it[0] < 128 {
                            1
                        } else {
                            std::str::from_utf8(it)
                                .ok()
                                .and_then(|s| s.chars().next())
                                .map(|c| c.len_utf8())
                                .unwrap_or(1)
                        };
                        self.update_coords(&old_input.input[..l]);
                        self.input.input = &self.input.input[l..];
                    }
                    return Some(TokInfo::new(
                        Token::ERRORTOKEN,
                        (start_offset, self.offset),
                        start_coords,
                        (self.line, self.col),
                        self.source_py.clone_ref(self.py()),
                    ));
                }
            }
        }
    }
}

pub fn tokenize(py: Python<'_>, source: Py<PyString>) -> Vec<TokInfo> {
    let source_bound = source.bind(py);
    let source_bytes = source_bound.to_str().unwrap().as_bytes();
    let mut t = Tokenizer::new(py, source.clone_ref(py), source_bytes);
    let mut tokens = Vec::new();
    while let Some(tok) = t.next_token() {
        tokens.push(tok);
    }
    tokens
}

#[pyfunction]
#[pyo3(name = "tokenize")]
pub fn tokenize_py(py: Python<'_>, source: Bound<'_, PyString>) -> Vec<TokInfo> {
    let source_bytes = source.to_str().unwrap().as_bytes();
    let mut t = Tokenizer::new(py, source.clone().into(), source_bytes);
    let mut tokens = Vec::new();
    while let Some(tok) = t.next_token() {
        tokens.push(tok);
    }
    tokens
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    #[test]
    fn test_infinite_loop() {
        Python::with_gil(|py| {
            let source = "from functools import wraps\n\n\ndef advanced_decorator(f):\n    @wraps(f)\n    def wrapper(*args, **kwargs):\n        print(\"Advanced decorator\")\n        return f(*args, **kwargs)\n\n    return wrapper\n\n\n@advanced_decorator\ndef decorated_function():\n    print(\"Decorated function\")\n";
            let py_source = pyo3::types::PyString::new(py, source).into();
            let tokens = tokenize(py, py_source);
            assert!(tokens.len() > 0);
        });
    }
}
