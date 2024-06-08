use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Token {
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
    Errortoken,
    Comment,
    NL,
    ENCODING,
    // xonsh specific tokens
    SearchPath,
    MacroParam,
    WS,
}

pub const OPERATORS: [&str; 60] = [
    "!=", "%", "%=", "&", "&=", "(", ")", "*", "**", "**=", "*=", "+", "+=", ",", "-", "-=", "->",
    ".", "...", "/", "//", "//=", "/=", ":", ":=", ";", "<", "<<", "<<=", "<=", "=", "==", ">",
    ">=", ">>", ">>=", "@", "@=", "[", "]", "^", "^=", "{", "|", "|=", "}", "~", "!", "$", "?",
    "??", "||", "&&", "@(", "!(", "![", "$(", "$[", "${", "@$(",
];

#[derive(Debug, Clone, PartialEq)]
struct TokInfo {
    typ: Token,
    string: String,
    start: (usize, usize),
    end: (usize, usize),
    line: String,
}

impl TokInfo {
    fn new(
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

    fn is_exact_type(&self, typ: &str) -> bool {
        self.typ == Token::OP && OPERATORS.contains(&typ)
    }

    fn loc_start(&self) -> HashMap<String, usize> {
        let mut map = HashMap::new();
        map.insert("lineno".to_string(), self.start.0);
        map.insert("col_offset".to_string(), self.start.1);
        map
    }

    fn loc_end(&self) -> HashMap<String, usize> {
        let mut map = HashMap::new();
        map.insert("end_lineno".to_string(), self.end.0);
        map.insert("end_col_offset".to_string(), self.end.1);
        map
    }

    fn loc(&self) -> HashMap<String, usize> {
        // merge loc_start and loc_end outputs
        let mut map = HashMap::new();
        map.extend(self.loc_start());
        map.extend(self.loc_end());
        map
    }

    fn is_next_to(&self, prev: &TokInfo) -> bool {
        self.end == prev.start
    }
}

#[derive(Debug, Clone)]
struct State<'a> {
    lnum: usize,
    parenlev: usize,
    continued: bool,
    indents: Vec<usize>,
    last_line: String,
    line: &'a str,
    pos: usize,
    max: usize,
    end_progs: Vec<EndProg>,
}

impl<'a> State<'a> {
    fn new() -> Self {
        Self {
            lnum: 0,
            parenlev: 0,
            continued: false,
            indents: vec![0],
            last_line: String::new(),
            line: "",
            pos: 0,
            max: 0,
            end_progs: vec![],
        }
    }

    fn move_next_line(&mut self, readline: &mut impl Iterator<Item = &'a str>) -> bool {
        self.last_line = self.line.to_string();
        if let Some(line) = readline.next() {
            self.line = line;
        } else {
            self.line = "";
            return false;
        }
        self.lnum += 1;
        self.pos = 0;
        self.max = self.line.len();
        true
    }

    fn add_prog(&mut self, start: usize, end: usize, pattern: &str, quote: &str, mode: Mode) {
        self.end_progs.push(EndProg::new(
            pattern.to_string(),
            self.line[start..end].to_string(),
            self.line.to_string(),
            (self.lnum, start),
            quote.to_string(),
            mode,
        ));
    }

    fn pop_mode(&mut self, end: Option<(usize, usize)>) -> Option<EndProg> {
        if let Some(prog) = self.end_progs.pop() {
            if let Some(end) = end {
                if let Some(last_prog) = self.end_progs.last_mut() {
                    last_prog.reset(end);
                }
            }
            Some(prog)
        } else {
            None
        }
    }

    fn match_pattern(&self, pattern: &str) -> Option<regex::Match> {
        let re = regex::Regex::new(pattern).unwrap();
        re.find(&self.line[self.pos..])
    }

    fn is_in_mode(&self, mode: Mode) -> bool {
        self.end_progs
            .last()
            .map_or(false, |prog| prog.mode == mode)
    }

    fn in_fstring(&self) -> bool {
        self.is_in_mode(Mode::ModeMiddle)
    }

    fn in_braces(&self) -> bool {
        self.is_in_mode(Mode::ModeInBraces)
    }

    fn in_colon(&self) -> bool {
        self.is_in_mode(Mode::ModeInColon)
    }
}

#[derive(Debug, Clone)]
struct EndProg {
    pattern: String,
    text: String,
    contline: String,
    start: (usize, usize),
    quote: String,
    mode: Mode,
}

impl EndProg {
    fn new(
        pattern: String,
        text: String,
        contline: String,
        start: (usize, usize),
        quote: String,
        mode: Mode,
    ) -> Self {
        Self {
            pattern,
            text,
            contline,
            start,
            quote,
            mode,
        }
    }

    fn join(&mut self, state: &State, end: usize) {
        self.text += &state.line[state.pos..end];
    }

    fn reset(&mut self, end: (usize, usize)) {
        self.start = end;
    }
}

#[derive(Debug, Clone, PartialEq)]
enum Mode {
    ModeMiddle,
    ModeInBraces,
    ModeInColon,
}
