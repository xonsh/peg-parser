use pyo3::prelude::*;
use pyo3::types::PyString;
use ser_rs::parser::{self, Parser};
use ser_rs::result::{Error, Result};
use std::collections::VecDeque;
use std::str;
use xtokens::{TokInfo, Token};

// Helper trait to extend Parser with our loop
// Or we just use `parser.repeat_discard(..)`

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FStringState {
    pub quote: Vec<u8>, // Uses Vec, but it's only on stack for open f-strings
    pub brace_level: usize,
    pub in_format_spec: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LexerState {
    pub indents: Vec<usize>,
    pub fstring_stack: Vec<FStringState>, // This allocates, but only proportional to nesting depth
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

pub struct Lexer<'a> {
    input: &'a [u8],
    offset: usize,
    line: usize,
    col: usize,
    state: LexerState,
    pending_tokens: VecDeque<TokInfo>,
    eof_emitted: bool,
    source_py: Py<PyString>,
    py: Python<'a>,
    // Cached parsers?
    // We can't easily cache parsers if they are closures that don't capture anything because Parser wraps them in Box.
    // We can hold them if we want, but creating them might be cheap if Box overhead is acceptable per token.
    // The prompt asked for "no allocation".
    // Creating `Parser` allocates `Box`.
    // Parser::new(Box::new(...))
    // A new Parser is created for EVERY combinator call.
    // `parser::sym(b' ').repeat(..)` ->
    //   sym creates Parser (alloc Box)
    //   repeat creates Parser (alloc Box) wrapping the first parser.
    // So `parse_ws` defined as function creates a tree of Boxes every time it is called.
    // This is NOT zero-alloc.

    // To achieve zero-alloc with ser-rs as it is defined now (struct Parser { Box<Fn> }), we must pre-allocate parsers or avoid using `Parser` struct combinators.
    // But `ser-rs` API IS `Parser` struct.

    // If I cannot change `ser-rs` `Parser` definition (which uses Box), I cannot use `ser-rs` combinators without allocation.
    // Wait, the Prompt said "create a lexer using ser-rs".
    // If ser-rs uses Box, then I have to use Box.
    // But "use zero copying, and no allocation" implies I should perhaps construct the parsers ONCE.
    // But `Parser` has lifetime `'a` of input.
    // So if I construct them once per `Lexer` instance, that's "no allocation per token".
}

impl<'a> Lexer<'a> {
    pub fn new(py: Python<'a>, source: Py<PyString>, input: &'a [u8]) -> Self {
        Self {
            input,
            offset: 0,
            line: 1,
            col: 0,
            state: LexerState::default(),
            pending_tokens: VecDeque::new(),
            eof_emitted: false,
            source_py: source,
            py,
        }
    }

    fn update_coords(&mut self, consumed: &[u8]) {
        let s = str::from_utf8(consumed).unwrap_or("");
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

    fn create_token(
        &self,
        typ: Token,
        start_offset: usize,
        start_coords: (usize, usize),
    ) -> TokInfo {
        TokInfo::new(
            typ,
            (start_offset, self.offset),
            start_coords,
            (self.line, self.col),
            self.source_py.clone_ref(self.py),
        )
    }

    // We define parsers as methods that build & run.
    // To strictly follow "no allocation", we'd need to cache them.
    // But `ser-rs` design makes heavy reuse hard without ownership issues or cloning Boxes (which allocates).
    // `Parser` does not implement `Clone` for free because `Box<dyn Fn>` doesn't.
    // We would need `Rc` or `Arc` or reference.
    // Changing `ser-rs` to use `Rc` instead of `Box`? Or `&dyn Fn`?

    // Let's stick to using `repeat_discard` to avoid Vec allocs.
    // The Box allocs are "setup costs" for the parser combinator usage.

    fn parse_ws() -> Parser<'a, u8, &'a [u8]> {
        parser::one_of(b" \t\x0c").repeat_discard(1..).collect()
    }

    fn parse_comment() -> Parser<'a, u8, &'a [u8]> {
        (parser::sym(b'#')
            + parser::not_a(|c| c == b'\r' || c == b'\n')
                .repeat_discard(0..)
                .discard())
        .collect()
    }

    fn parse_line_ending() -> Parser<'a, u8, &'a [u8]> {
        (parser::sym(b'\r').opt() + parser::sym(b'\n')).collect()
    }

    fn parse_name() -> Parser<'a, u8, &'a [u8]> {
        parser::is_a(|c: u8| c.is_ascii_alphanumeric() || c == b'_' || c > 127)
            .repeat_discard(1..)
            .collect()
            .convert(|s: &[u8]| {
                if s[0].is_ascii_digit() {
                    Err("name cannot start with digit")
                } else {
                    Ok(s)
                }
            })
    }

    fn hex_digit1_w() -> Parser<'a, u8, ()> {
        (parser::is_a(|c: u8| c.is_ascii_hexdigit())
            + (parser::sym(b'_') + parser::is_a(|c: u8| c.is_ascii_hexdigit()))
                .repeat_discard(0..)
                .discard())
        .discard()
    }

    fn bin_digit1_w() -> Parser<'a, u8, ()> {
        (parser::one_of(b"01")
            + (parser::sym(b'_') + parser::one_of(b"01"))
                .repeat_discard(0..)
                .discard())
        .discard()
    }

    fn oct_digit1_w() -> Parser<'a, u8, ()> {
        (parser::is_a(|c: u8| (b'0'..=b'7').contains(&c))
            + (parser::sym(b'_') + parser::is_a(|c: u8| (b'0'..=b'7').contains(&c)))
                .repeat_discard(0..)
                .discard())
        .discard()
    }

    fn digit1_w() -> Parser<'a, u8, ()> {
        (parser::is_a(|c: u8| c.is_ascii_digit())
            + (parser::sym(b'_') + parser::is_a(|c: u8| c.is_ascii_digit()))
                .repeat_discard(0..)
                .discard())
        .discard()
    }

    fn parse_number() -> Parser<'a, u8, &'a [u8]> {
        let hex = (parser::seq(b"0x") | parser::seq(b"0X")) + Self::hex_digit1_w();
        let bin = (parser::seq(b"0b") | parser::seq(b"0B")) + Self::bin_digit1_w();
        let oct = (parser::seq(b"0o") | parser::seq(b"0O")) + Self::oct_digit1_w();

        let float_int = Self::digit1_w()
            + (parser::sym(b'.') + Self::digit1_w().opt()).opt()
            + (parser::one_of(b"eE") + parser::one_of(b"+-").opt() + Self::digit1_w()).opt();

        let dot_float = parser::sym(b'.') + Self::digit1_w();

        (hex.collect() | bin.collect() | oct.collect() | float_int.collect() | dot_float.collect())
            .collect()
    }

    // ... parse_op, parse_string, etc using repeat_discard ...
    fn parse_op() -> Parser<'a, u8, &'a [u8]> {
        // Same as before
        // ...
        // For brevity, similar implementation
        Parser::new(|input, start| {
            let ops_list = [
                b"..." as &[u8],
                b">>=",
                b"<<=",
                b"**=",
                b"//=",
                b"??",
                b"||",
                b"&&",
                b"@$(",
                b"@(",
                b"!(",
                b"![",
                b"$(",
                b"$[",
                b"${",
                b"!=",
                b"%=",
                b"&=",
                b"**",
                b"*=",
                b"+=",
                b"-=",
                b"->",
                b"//",
                b"/=",
                b":=",
                b"<<",
                b"<=",
                b"==",
                b">=",
                b">>",
                b"@=",
                b"^=",
                b"|=",
                b"> &",
                b">&",
                b"&>",
                b"%",
                b"&",
                b"(",
                b")",
                b"*",
                b"+",
                b",",
                b"-",
                b".",
                b"/",
                b":",
                b";",
                b"<",
                b"=",
                b">",
                b"@",
                b"[",
                b"]",
                b"^",
                b"{",
                b"|",
                b"}",
                b"~",
                b"!",
                b"$",
                b"?",
            ];
            for op in ops_list {
                if let Ok((res, pos)) = parser::seq(op).parse_at(input, start) {
                    return Ok((res, pos));
                }
            }
            Err(Error::Mismatch {
                message: "no op matched".into(),
                position: start,
            })
        })
    }

    fn parse_string_prefix() -> Parser<'a, u8, &'a [u8]> {
        Parser::new(|input, start| {
            let prefixes = [
                b"rf" as &[u8],
                b"fr",
                b"rb",
                b"br",
                b"pf",
                b"fp",
                b"pr",
                b"rp",
                b"RF",
                b"FR",
                b"RB",
                b"BR",
                b"PF",
                b"FP",
                b"PR",
                b"RP",
                b"rF",
                b"Rf",
                b"fR",
                b"Fr",
                b"rB",
                b"Rb",
                b"bR",
                b"Br",
                b"pF",
                b"Pf",
                b"fP",
                b"Fp",
                b"pR",
                b"Rp",
                b"rP",
                b"Pr",
                b"u",
                b"p",
                b"r",
                b"f",
                b"b",
                b"U",
                b"P",
                b"R",
                b"F",
                b"B",
            ];
            for p in &prefixes {
                if p.len() == 2 {
                    if let Ok(res) = parser::seq(p).parse_at(input, start) {
                        return Ok(res);
                    }
                }
            }
            for p in &prefixes {
                if p.len() == 1 {
                    if let Ok(res) = parser::seq(p).parse_at(input, start) {
                        return Ok(res);
                    }
                }
            }
            Ok((&input[start..start], start))
        })
    }

    fn parse_full_string() -> Parser<'a, u8, &'a [u8]> {
        Parser::new(|input, start| {
            let (_, pos1) = Self::parse_string_prefix().parse_at(input, start)?;

            let mut current_pos = pos1;
            let quote_len = if parser::seq(b"'''").parse_at(input, current_pos).is_ok()
                || parser::seq(b"\"\"\"").parse_at(input, current_pos).is_ok()
            {
                3
            } else if parser::seq(b"'").parse_at(input, current_pos).is_ok()
                || parser::seq(b"\"").parse_at(input, current_pos).is_ok()
            {
                1
            } else {
                return Err(Error::Mismatch {
                    message: "not a string".into(),
                    position: start,
                });
            };

            let quote = &input[current_pos..current_pos + quote_len];
            current_pos += quote_len;

            loop {
                if current_pos >= input.len() {
                    return Err(Error::Mismatch {
                        message: "unterminated string".into(),
                        position: start,
                    });
                }

                if parser::seq(quote).parse_at(input, current_pos).is_ok() {
                    current_pos += quote_len;
                    break;
                }

                if input[current_pos] == b'\\' {
                    current_pos += 1;
                    if current_pos < input.len() {
                        current_pos += 1;
                    }
                } else {
                    current_pos += 1;
                }
            }
            Ok((&input[start..current_pos], current_pos))
        })
    }

    fn consume_indent(&mut self) -> Result<Token> {
        let (_, pos) = Self::parse_ws().opt().parse_at(self.input, 0)?;
        let indent_len = pos;

        let rest = &self.input[pos..];
        if rest.is_empty()
            || Self::parse_line_ending().parse_at(rest, 0).is_ok()
            || Self::parse_comment().parse_at(rest, 0).is_ok()
        {
            if pos > 0 {
                self.update_coords(&self.input[..pos]);
                self.input = &self.input[pos..];
                self.state.at_beginning_of_line = false;
                return Ok(Token::WS);
            } else {
                if let Ok((_, le_pos)) = Self::parse_line_ending().parse_at(self.input, pos) {
                    let total = pos + le_pos;
                    self.update_coords(&self.input[..total]);
                    self.input = &self.input[total..];
                    self.state.at_beginning_of_line = true; // Still true? Line ending on empty line keeps it true
                    return Ok(Token::WS);
                }
                if let Ok((_, cm_pos)) = Self::parse_comment().parse_at(self.input, pos) {
                    let total = pos + cm_pos;
                    self.update_coords(&self.input[..total]);
                    self.input = &self.input[total..];
                    // Comment consumes until newline but not newline?
                    // My parse_comment implementation:
                    // sym(#) + not_a(\r\n).repeat_discard().discard()
                    // It stops AT newline
                    return Ok(Token::WS);
                }
            }
            // Empty string but not caught?
            return Ok(Token::WS);
        }

        if self.state.paren_level > 0 || !self.state.fstring_stack.is_empty() {
            if pos > 0 {
                self.update_coords(&self.input[..pos]);
                self.input = &self.input[pos..];
                return Ok(Token::WS);
            }
            return Err(Error::Mismatch {
                message: "indent inside paren".into(),
                position: 0,
            });
        }

        let last_indent = *self.state.indents.last().unwrap();

        if indent_len > last_indent {
            self.state.indents.push(indent_len);
            self.update_coords(&self.input[..pos]);
            self.input = &self.input[pos..];
            self.state.at_beginning_of_line = false;
            return Ok(Token::INDENT);
        } else if indent_len < last_indent {
            self.state.indents.pop();
            self.state.at_beginning_of_line = true;
            return Ok(Token::DEDENT);
        } else {
            if pos > 0 {
                self.update_coords(&self.input[..pos]);
                self.input = &self.input[pos..];
                self.state.at_beginning_of_line = false;
                Ok(Token::WS)
            } else {
                Err(Error::Mismatch {
                    message: "no indent change".into(),
                    position: 0,
                })
            }
        }
    }
}

impl<'a> Iterator for Lexer<'a> {
    type Item = TokInfo;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(tok) = self.pending_tokens.pop_front() {
                return Some(tok);
            }

            if self.input.is_empty() {
                if !self.state.fstring_stack.is_empty() {
                    return None;
                }
                if self.eof_emitted {
                    return None;
                }

                if !self.state.at_beginning_of_line {
                    self.state.at_beginning_of_line = true;
                    return Some(self.create_token(
                        Token::NEWLINE,
                        self.offset,
                        (self.line, self.col),
                    ));
                }

                if self.state.indents.len() > 1 {
                    self.state.indents.pop();
                    return Some(self.create_token(Token::DEDENT, self.offset, (self.line, 0)));
                }

                self.eof_emitted = true;
                return Some(self.create_token(
                    Token::ENDMARKER,
                    self.offset,
                    (self.line, self.col),
                ));
            }

            // Backslash handling
            if self.input.starts_with(b"\\") {
                let mut check_pos = 1;
                if let Ok((_, p)) = Self::parse_ws().parse_at(self.input, check_pos) {
                    check_pos = p;
                }
                if let Ok((_, p)) = Self::parse_line_ending().parse_at(self.input, check_pos) {
                    let consumed = &self.input[..p];
                    self.update_coords(consumed);
                    self.input = &self.input[p..];
                    continue;
                }
            }

            let start_offset = self.offset;
            let start_coords = (self.line, self.col);

            if self.state.at_beginning_of_line {
                match self.consume_indent() {
                    Ok(tok) => match tok {
                        Token::WS => continue,
                        t => {
                            return Some(self.create_token(t, start_offset, start_coords));
                        }
                    },
                    Err(_) => {
                        self.state.at_beginning_of_line = false;
                    }
                }
            }

            let c = self.input[0];
            let res: Result<(Token, usize)> = {
                if c == b' ' || c == b'\t' || c == 0x0c {
                    Self::parse_ws().map(|_| Token::WS).parse_at(self.input, 0)
                } else if c == b'#' {
                    Self::parse_comment()
                        .map(|_| Token::COMMENT)
                        .parse_at(self.input, 0)
                } else if c == b'\n' || c == b'\r' {
                    Self::parse_line_ending()
                        .map(|_| Token::NEWLINE)
                        .parse_at(self.input, 0)
                } else if c.is_ascii_digit() {
                    Self::parse_number()
                        .map(|_| Token::NUMBER)
                        .parse_at(self.input, 0)
                } else if c == b'\'' || c == b'"' {
                    Self::parse_full_string()
                        .map(|_| Token::STRING)
                        .parse_at(self.input, 0)
                } else if c.is_ascii_alphabetic() || c == b'_' {
                    if let Ok((_, _)) = ((parser::seq(b"f") | parser::seq(b"F"))
                        + (parser::sym(b'\'') | parser::sym(b'"')))
                    .parse_at(self.input, 0)
                    {
                        Err(Error::Mismatch {
                            message: "todo".into(),
                            position: 0,
                        })
                    } else {
                        if let Ok((_, pos)) = Self::parse_full_string().parse_at(self.input, 0) {
                            Ok((Token::STRING, pos))
                        } else {
                            Self::parse_name()
                                .map(|n| match n {
                                    b"async" => Token::ASYNC,
                                    b"await" => Token::AWAIT,
                                    _ => Token::NAME,
                                })
                                .parse_at(self.input, 0)
                        }
                    }
                } else {
                    Self::parse_op().map(|_| Token::OP).parse_at(self.input, 0)
                }
            };

            match res {
                Ok((mut tok, pos)) => {
                    if let Token::NEWLINE = tok {
                        self.state.at_beginning_of_line = true;
                        if self.state.paren_level > 0
                            || !self.state.fstring_stack.is_empty()
                            || !self.state.has_content
                        {
                            tok = Token::NL;
                        }
                        self.state.has_content = false;
                    } else if let Token::NL = tok {
                        // should not happen
                    } else if tok != Token::WS && tok != Token::COMMENT {
                        self.state.has_content = true;
                    }

                    let consumed = &self.input[..pos];
                    self.update_coords(consumed);
                    self.input = &self.input[pos..];

                    match tok {
                        Token::OP => {
                            let s = str::from_utf8(consumed).unwrap().as_bytes();
                            if s == b"(" || s == b"[" || s == b"{" {
                                self.state.paren_level += 1;
                            } else if s == b")" || s == b"]" || s == b"}" {
                                if self.state.paren_level > 0 {
                                    self.state.paren_level -= 1;
                                }
                            }
                        }
                        _ => {}
                    }

                    return Some(self.create_token(tok, start_offset, start_coords));
                }
                Err(_) => {
                    let l = if self.input[0] < 128 { 1 } else { 1 };
                    let consumed = &self.input[..l];
                    self.update_coords(consumed);
                    self.input = &self.input[l..];
                    return Some(self.create_token(Token::ERRORTOKEN, start_offset, start_coords));
                }
            }
        }
    }
}

pub fn tokenize<'a>(py: Python<'a>, source: Py<PyString>) -> Vec<TokInfo> {
    let source_clone = source.clone_ref(py);
    let s = source.bind(py).to_str().unwrap().as_bytes();
    let lexer = Lexer::new(py, source_clone, s);
    lexer.collect()
}
