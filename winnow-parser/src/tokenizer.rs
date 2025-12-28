use pyo3::prelude::*;
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
    ErrorToken,
    Comment,
    NL,
    // xonsh specific tokens
    SEARCH_PATH,
    WS,
    MacroParam,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FStringState {
    pub quote: String,
    pub brace_level: usize,
    pub in_format_spec: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LexerState {
    pub indents: Vec<usize>,
    pub fstring_stack: Vec<FStringState>,
    pub paren_level: usize,
    pub at_beginning_of_line: bool,
}

impl Default for LexerState {
    fn default() -> Self {
        Self {
            indents: vec![0],
            fstring_stack: Vec::new(),
            paren_level: 0,
            at_beginning_of_line: true,
        }
    }
}

pub type Stream<'s> = Stateful<&'s str, LexerState>;

#[pyclass(get_all)]
#[derive(Debug, Clone, PartialEq)]
pub struct TokInfo {
    pub typ: Token,
    pub span: (usize, usize),
    pub start: (usize, usize),
    pub end: (usize, usize),
}

#[pymethods]
impl TokInfo {
    #[new]
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

    fn __repr__(&self) -> String {
        format!(
            "TokInfo(typ={:?}, span={:?}, start={:?}, end={:?})",
            self.typ, self.span, self.start, self.end
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

// ... helper parsers ...
pub fn oct_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    (
        take_while(1.., '0'..='7'),
        repeat(0.., ("_", take_while(1.., '0'..='7'))).map(|_: ()| ()),
    )
        .take()
        .parse_next(input)
}

pub fn bin_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    (
        take_while(1.., '0'..='1'),
        repeat(0.., ("_", take_while(1.., '0'..='1'))).map(|_: ()| ()),
    )
        .take()
        .parse_next(input)
}

pub fn hex_digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    (hex_digit1, repeat(0.., ("_", hex_digit1)).map(|_: ()| ()))
        .take()
        .parse_next(input)
}

pub fn digit1_w<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    (digit1, repeat(0.., ("_", digit1)).map(|_: ()| ()))
        .take()
        .parse_next(input)
}

pub fn parse_ws<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    take_while(1.., (' ', '\t', '\x0c')).parse_next(input)
}

pub fn parse_comment<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    ("#", take_while(0.., |c| c != '\r' && c != '\n'))
        .take()
        .parse_next(input)
}

pub fn parse_name<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    let res = take_while(1.., |c: char| c.is_alphanumeric() || c == '_')
        .verify(|s: &str| {
            let c = s.chars().next().unwrap();
            !c.is_ascii_digit()
        })
        .parse_next(input);

    if res.is_ok() {
        input.state.at_beginning_of_line = false;
    }
    res
}

pub fn parse_number<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    let res = alt((
        (alt(("0x", "0X")), hex_digit1_w).take(),
        (alt(("0b", "0B")), bin_digit1_w).take(),
        (alt(("0o", "0O")), oct_digit1_w).take(),
        (
            digit1_w,
            opt((".", opt(digit1_w))),
            opt((alt(('e', 'E')), opt(alt(('+', '-'))), digit1_w)),
        )
            .take(),
        (".", digit1_w).take(),
    ))
    .parse_next(input);

    if res.is_ok() {
        input.state.at_beginning_of_line = false;
    }
    res
}

pub fn parse_op<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    let op: &str = alt((
        alt(("...", ">>=", "<<=", "**=", "//=", "??", "||", "&&")),
        alt(("@$(", "@(", "!(", "![", "$(", "$[", "${", "!=")),
        alt(("%=", "&=", "**", "*=", "+=", "-=", "->", "//")),
        alt(("/=", ":=", "<<", "<=", "==", ">=", ">>", "@=")),
        alt(("^=", "|=", "%", "&", "(", ")", "*", "+")),
        alt(("> &", ">&", "&>", ",")),
        alt(("-", ".", "/", ":", ";", "<", "=")),
        alt((">", "@", "[", "]", "^", "{", "|", "}")),
        alt(("~", "!", "$", "?")),
    ))
    .parse_next(input)?;

    let state = &mut input.state;
    state.at_beginning_of_line = false;

    if op == "(" || op == "[" || op == "{" {
        state.paren_level += 1;
    } else if op == ")" || op == "]" || op == "}" {
        state.paren_level = state.paren_level.saturating_sub(1);
    }

    let fs_len = state.fstring_stack.len();
    if let Some(f_state) = state.fstring_stack.last_mut() {
        if f_state.brace_level > 0 {
            if op == "{" {
                f_state.brace_level += 1;
            } else if op == "}" {
                f_state.brace_level -= 1;
                if f_state.brace_level == 0 && f_state.in_format_spec {
                    f_state.in_format_spec = false;
                }
            } else if op == ":" && f_state.brace_level == 1 && state.paren_level == fs_len {
                f_state.in_format_spec = true;
                f_state.brace_level = 0;
            }
        }
    }

    Ok(op)
}

pub fn parse_string_prefix<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    alt((
        alt((
            "rf", "fr", "rb", "br", "pF", "Fp", "pf", "fp", "pr", "rp", "r", "f", "b", "u", "p",
        )),
        alt((
            "RF", "FR", "RB", "BR", "PF", "FP", "PR", "RP", "R", "F", "B", "U", "P",
        )),
        "",
    ))
    .parse_next(input)
}

pub fn parse_full_string<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    let start = input.input;
    let _ = parse_string_prefix(input)?;
    let quote_len = if input.starts_with("'''") || input.starts_with("\"\"\"") {
        3
    } else if input.starts_with('\'') || input.starts_with('"') {
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
        if input.starts_with('\\') {
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

pub fn parse_search_path<'s>(input: &mut Stream<'s>) -> ModalResult<&'s str> {
    let res = (
        opt(alt((
            take_while(1.., ('r', 'g', 'p', 'f')),
            ("@", take_while(0.., ('a'..='z', 'A'..='Z', '0'..='9', '_'))).take(),
        ))),
        "`",
        take_until(0.., "`"),
        "`",
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
    let ws_res: Result<&str, ErrMode<winnow::error::ContextError>> = parse_ws(&mut check_empty);
    let (indent_len, new_input) = match ws_res {
        Ok(ws) => (ws.len(), check_empty),
        Err(_) => (0, input.clone()),
    };

    let mut check_content = new_input.clone();
    let le_res: Result<&str, ErrMode<winnow::error::ContextError>> =
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

    if state_in_format_spec && input.starts_with('}') {
        input.input = &input.input[1..];
        let state_mut = input.state.fstring_stack.last_mut().unwrap();
        state_mut.in_format_spec = false;
        state_mut.brace_level = 0;
        input.state.paren_level = input.state.paren_level.saturating_sub(1);
        return Ok(Token::OP);
    }

    if !state_in_format_spec && input.starts_with('{') {
        input.input = &input.input[1..];
        let state_mut = input.state.fstring_stack.last_mut().unwrap();
        state_mut.brace_level = 1;
        state_mut.in_format_spec = false;
        input.state.paren_level += 1;
        return Ok(Token::OP);
    }

    let mut temp_input = input.clone();
    let mut len = 0;
    while !temp_input.is_empty() {
        let curr_quote = &input.state.fstring_stack.last().unwrap().quote;

        if (!state_in_format_spec && temp_input.starts_with('{'))
            || temp_input.starts_with(curr_quote)
        {
            break;
        }
        if state_in_format_spec && temp_input.starts_with('}') {
            break;
        }

        if temp_input.starts_with('\\') {
            len += 1;
            temp_input.input = &temp_input.input[1..];
            if !temp_input.is_empty() {
                let c = temp_input.chars().next().unwrap();
                len += c.len_utf8();
                temp_input.input = &temp_input.input[c.len_utf8()..];
            }
        } else {
            let c = temp_input.chars().next().unwrap();
            len += c.len_utf8();
            temp_input.input = &temp_input.input[c.len_utf8()..];
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

    if !prefix.to_ascii_lowercase().contains('f') || check.is_empty() {
        return Err(ErrMode::Backtrack(winnow::error::ContextError::new()));
    }

    let ql = if check.starts_with("'''") || check.starts_with("\"\"\"") {
        3
    } else if check.starts_with('\'') || check.starts_with('"') {
        1
    } else {
        0
    };

    if ql > 0 {
        let quote = &check.input[..ql];
        let quote_str = quote.to_string();
        input.input = &check.input[ql..];

        input.state.fstring_stack.push(FStringState {
            quote: quote_str,
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
    if input.state.paren_level > 0 || !input.state.fstring_stack.is_empty() {
        Ok(Token::NL)
    } else {
        Ok(Token::NEWLINE)
    }
}

pub struct Tokenizer<'s> {
    input: Stream<'s>,
    offset: usize,
    line: usize,
    col: usize,
    pending_tokens: std::collections::VecDeque<TokInfo>,
    eof_emitted: bool,
}

impl<'s> Tokenizer<'s> {
    pub fn new(source: &'s str) -> Self {
        Self {
            input: Stateful {
                input: source,
                state: LexerState::default(),
            },
            offset: 0,
            line: 1,
            col: 0,
            pending_tokens: std::collections::VecDeque::new(),
            eof_emitted: false,
        }
    }

    fn update_coords(&mut self, consumed: &str) {
        for c in consumed.chars() {
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
                    ));
                }

                if self.input.state.indents.len() > 1 {
                    self.input.state.indents.pop();
                    return Some(TokInfo::new(
                        Token::DEDENT,
                        (self.offset, self.offset),
                        (self.line, 0),
                        (self.line, 0),
                    ));
                }

                self.eof_emitted = true;
                return Some(TokInfo::new(
                    Token::ENDMARKER,
                    (self.offset, self.offset),
                    (self.line, self.col),
                    (self.line, self.col),
                ));
            }

            if self.input.starts_with('\\') {
                let mut check = self.input.clone();
                let _: Result<char, ErrMode<winnow::error::ContextError>> =
                    any.parse_next(&mut check);
                let mut skipped_len = 1;
                let r_ws: Result<&str, ErrMode<winnow::error::ContextError>> = parse_ws(&mut check);
                if let Ok(ws) = r_ws {
                    skipped_len += ws.len();
                }
                let r_le: Result<&str, ErrMode<winnow::error::ContextError>> =
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

            // Refactored Dispatch Logic

            // Priority 1: Indentation (State Check)
            let result: Result<Token, ErrMode<winnow::error::ContextError>> =
                if self.input.state.at_beginning_of_line {
                    let initial_input = self.input.clone();
                    let _res = parse_indentation(&mut self.input);
                    if _res.is_ok() {
                        _res
                    } else {
                        self.input = initial_input; // Restore state (including at_beginning_of_line)

                        dispatch! { peek(any);
                            ' ' | '\t' | '\x0c' => parse_ws.map(|_| Token::WS),
                            '#' => parse_comment.map(|_| Token::Comment),
                            '\n' | '\r' => parse_line_ending_token,
                            '0'..='9' => parse_number.map(|_| Token::NUMBER),
                            'a'..='z' | 'A'..='Z' | '_' => alt((
                                parse_fstring_start,
                                // identifiers can start search path?
                                parse_search_path.map(|_| Token::SEARCH_PATH),
                                parse_full_string.map(|_| Token::STRING),
                                parse_name.map(|_| Token::NAME)
                            )),
                            '\'' | '"' => alt((
                                 parse_fstring_start,
                                 parse_full_string.map(|_| Token::STRING)
                            )),
                            '`' => parse_search_path.map(|_| Token::SEARCH_PATH),
                            '@' => alt((
                                parse_search_path.map(|_| Token::SEARCH_PATH),
                                parse_op.map(|_| Token::OP)
                            )),
                            '.' => alt((
                                parse_number.map(|_| Token::NUMBER),
                                parse_op.map(|_| Token::OP)
                            )),
                            _ => alt((
                                parse_op.map(|_| Token::OP),
                                any.map(|_| Token::ErrorToken)
                            ))
                        }
                        .parse_next(&mut self.input)
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
                        ' ' | '\t' | '\x0c' => parse_ws.map(|_| Token::WS),
                        '#' => parse_comment.map(|_| Token::Comment),
                        '\n' | '\r' => parse_line_ending_token,
                        '0'..='9' => parse_number.map(|_| Token::NUMBER),
                        'a'..='z' | 'A'..='Z' | '_' => alt((
                            parse_fstring_start,
                            parse_search_path.map(|_| Token::SEARCH_PATH),
                            parse_full_string.map(|_| Token::STRING),
                            parse_name.map(|_| Token::NAME)
                        )),
                        '\'' | '"' => alt((
                             parse_fstring_start,
                             parse_full_string.map(|_| Token::STRING)
                        )),
                        '`' => parse_search_path.map(|_| Token::SEARCH_PATH),
                        '@' => alt((
                            parse_search_path.map(|_| Token::SEARCH_PATH),
                            parse_op.map(|_| Token::OP)
                        )),
                        '.' => alt((
                            parse_number.map(|_| Token::NUMBER),
                            parse_op.map(|_| Token::OP)
                        )),
                        _ => alt((
                            parse_op.map(|_| Token::OP),
                            any.map(|_| Token::ErrorToken)
                        ))
                    }
                    .parse_next(&mut self.input)
                };

            let consumed_len = old_input.input.len() - self.input.input.len();
            let consumed = &old_input.input[..consumed_len];

            self.update_coords(consumed);

            match result {
                Ok(Token::WS) | Ok(Token::NL) => {
                    continue;
                }
                Ok(tok) => {
                    return Some(TokInfo::new(
                        tok,
                        (start_offset, self.offset),
                        start_coords,
                        (self.line, self.col),
                    ));
                }
                Err(_) => {
                    return Some(TokInfo::new(
                        Token::ErrorToken,
                        (start_offset, self.offset),
                        start_coords,
                        (self.line, self.col),
                    ));
                }
            }
        }
    }
}

pub fn tokenize<'s>(source: &'s str) -> Vec<TokInfo> {
    let mut t = Tokenizer::new(source);
    let mut tokens = Vec::new();
    while let Some(tok) = t.next_token() {
        tokens.push(tok);
    }
    tokens
}

#[pyfunction]
#[pyo3(name = "tokenize")]
pub fn tokenize_py(source: &str) -> Vec<TokInfo> {
    tokenize(source)
}
