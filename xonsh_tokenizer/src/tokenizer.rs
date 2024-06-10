// use std::any::type_name;
use std::collections::HashMap;
use std::collections::VecDeque;
use std::fs::File;
use std::io::{BufRead, BufReader, Cursor, Read};
use std::iter::Iterator;
use std::mem::{Discriminant, discriminant};

use crate::regex::consts::{END_PATTERNS, END_RBRACE, Mode, OPERATORS, PSEUDO_TOKENS, START_LBRACE, TABSIZE};
use crate::regex::fns::{choice, compile};

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
    // AWAIT,
    // ASYNC,
    // TypeIgnore,
    // TypeComment,
    // SoftKeyword,
    FstringStart,
    FstringMiddle,
    FstringEnd,
    ErrorToken,
    Comment,
    NL,
    // ENCODING,
    // xonsh specific tokens
    SearchPath,
    // MacroParam,
    WS,
}


#[derive(Debug, Clone, PartialEq)]
struct TokInfo {
    typ: Token,
    string: String,
    start: (usize, usize),
    end: (usize, usize),
    // line: String,
}

#[allow(unused)]
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
            // line,
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

#[derive(Debug)]
struct Match {
    // overall match
    start: usize,
    end: usize,
    name: String, // name of the pattern matched
    text: String,
    // group names in this match
    sub_names: HashMap<String, String>,
}

#[derive(Debug, Clone)]
struct LineState {
    text: String,
    num: usize, // line number
    pos: usize, // current position in line
    max: usize, // max position in line
}

impl Default for LineState {
    fn default() -> Self {
        Self::new("", 0)
    }
}

impl LineState {
    fn new(line: &str, num: usize) -> Self {
        Self {
            text: line.to_string(),
            num,
            pos: 0,
            max: line.len(),
        }
    }
}

#[derive(Debug)]
struct State {
    parenlev: usize,
    continued: bool,
    indents: Vec<usize>,
    last_line: Option<LineState>,
    line: LineState,
    end_progs: Vec<EndProg>,
}

impl Default for State {
    fn default() -> Self {
        Self {
            parenlev: 0,
            continued: false,
            indents: vec![0],
            last_line: None,
            line: LineState::default(),
            end_progs: vec![],
        }
    }
}

impl State {
    fn at_parenlev(&self) -> bool {
        if let Some(mode) = self.current_mode() {
            if let Mode::InBraces(level) = *mode {
                return level == self.parenlev;
            }
        }
        return false;
    }
    fn set_line(&mut self, line: String) {
        if self.line.num != 0 {
            self.last_line = Some(self.line.clone());
        }
        self.line = LineState::new(line.as_str(), self.line.num + 1);
    }

    fn add_prog(&mut self, start: usize, end: usize, pattern: &str, quote: &str, mode: Mode) {
        self.end_progs.push(EndProg::new(
            pattern.to_string(),
            self.line.text[start..end].to_string(),
            self.line.text.to_string(),
            (self.line.num, start),
            quote.to_string(),
            mode,
        ));
    }

    fn pop_prog(&mut self) -> &mut Self {
        self.end_progs.pop();
        // return self for builder pattern
        self
    }

    fn reset_prog(&mut self, end: (usize, usize)) {
        if let Some(last_prog) = self.end_progs.last_mut() {
            last_prog.reset(end)
        }
    }

    fn prog_token(&mut self, end: usize, typ: Token) -> TokInfo {
        let endprog = self.end_progs.last_mut().unwrap();
        endprog.join(&self.line, end);
        self.line.pos = end;
        let epos = (self.line.num, end);
        return TokInfo {
            typ,
            string: endprog.text.clone(),
            start: endprog.start.clone(),
            end: epos,
            // line: endprog.contline.clone(),
        };
    }

    fn match_pattern(&self, pattern: &str) -> Option<Match> {
        let re = compile(pattern);
        let captures = re.captures(&self.line.text[self.line.pos..])?;
        let m = captures.get(0)?;
        let mut matches = HashMap::new(); // name -> value
        let mut first_name = "".to_string();
        for name in re.capture_names().flatten() {
            if let Some(m) = captures.name(name) {
                if first_name.is_empty() {
                    first_name = name.to_string();
                } else {
                    matches.insert(name.to_string(), m.as_str().to_string());
                }
            }
        }
        Some(Match { start: m.start() + self.line.pos, end: m.end() + self.line.pos, name: first_name, text: m.as_str().to_string(), sub_names: matches })
    }

    fn current_mode(&self) -> Option<&Mode> {
        let prog = self.end_progs.last()?;
        Some(&prog.mode)
    }
    fn is_in_mode(&self, variant: Discriminant<Mode>) -> bool {
        if let Some(mode) = self.current_mode() {
            return discriminant(mode) == variant;
        }
        return false;
    }

    fn in_fstring(&self) -> bool {
        return self.is_in_mode(discriminant(&Mode::Middle));
    }

    fn in_braces(&self) -> bool {
        return self.is_in_mode(discriminant(&Mode::InBraces(0)));
    }

    fn in_colon(&self) -> bool {
        return self.is_in_mode(discriminant(&Mode::InColon));
    }

    fn in_multi_line_string(&self) -> bool {
        return self.end_progs.last().map(|m| m.quote.len() == 3).unwrap_or(false);
    }

    fn in_continued_string(&self) -> bool {
        return self.end_progs.last().is_some() && (self.line.text.ends_with("\\\n") || self.line.text.ends_with("\\\r\n"));
    }
    fn collect_until(&mut self) -> Result<Vec<TokInfo>, String> {
        let mut pos = self.line.pos;
        let mut results = Vec::new();
        while self.line.pos < self.line.max {
            let res = handle_end_progs(self)?;
            results.extend(res);

            if let Some(t) = next_psuedo_matches(self)? {
                results.push(t);
            } else if pos == self.line.pos {
                pos = self.line.pos + 1;
                results.push(TokInfo {
                    typ: Token::ErrorToken,
                    string: self.line.text[self.line.pos..pos].to_string(),
                    start: (self.line.num, self.line.pos),
                    end: (self.line.num, pos),
                    // line: self.line.text.to_string(),
                });
                self.line.pos = pos;
            }
            // else {return Err(format!("Invalid tokenizer state at {}:{}", self.line.num, self.line.pos));}
        }
        return Ok(results);
    }
    fn collect_for(&mut self, line: String) -> Result<Vec<TokInfo>, String> {
        self.set_line(line);
        let mut results = Vec::new();

        if !self.end_progs.is_empty() {
            let res = handle_end_progs(self)?;
            results.extend(res);
        } else if self.parenlev == 0 && !self.continued {
            match next_statement(self)? {
                (LoopAction::Break, res) => {
                    results.extend(res);
                    return Ok(results);
                }
                (_, res) => {
                    results.extend(res);
                }
            }
        } else { // continued statement
            if self.line.text.is_empty() {
                return Err(format!("EOF in multi-line statement {}:{}", self.line.num, self.line.pos));
            }
            self.continued = false;
        }
        let res = self.collect_until()?; // store in a variable to debug
        results.extend(res);
        Ok(results)
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


enum LoopAction {
    Break,
    None,
}

type LoopResult = (LoopAction, Vec<TokInfo>);

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

    fn join(&mut self, line: &LineState, end: usize) {
        self.text += &line.text[line.pos..end];
    }

    fn join_line(&mut self, line: &LineState) {
        self.text += &line.text[line.pos..];
        self.contline += &line.text;
    }

    fn reset(&mut self, end: (usize, usize)) {
        self.start = end;
    }
}

fn next_statement(state: &mut State) -> Result<LoopResult, String> {
    let mut stash: Vec<TokInfo> = Vec::new();
    if state.line.text.is_empty() {
        return Ok((LoopAction::Break, stash));
    }
    let mut col = 0;

    // measure leading whitespace
    while state.line.pos < state.line.max {
        match state.line.text.chars().nth(state.line.pos).unwrap() {
            ' ' => col += 1,
            '\t' => col = (col / TABSIZE + 1) * TABSIZE,
            '\u{C}' => col = 0, // form feed '\f'
            _ => break,
        }
        state.line.pos += 1;
    }
    if state.line.pos == state.line.max {
        return Ok((LoopAction::Break, stash));
    }

    let current_char = state.line.text.chars().nth(state.line.pos).unwrap();
    if "#\r\n".contains(current_char) {
        if current_char == '#' {
            let comment_token = state.line.text[state.line.pos..].trim_end_matches("\r\n");
            stash.push(TokInfo::new(
                Token::Comment,
                comment_token.to_string(),
                (state.line.num, state.line.pos),
                (state.line.num, state.line.pos + comment_token.len()),
                state.line.text.to_string().clone(),
            ));
        }
        stash.push(TokInfo::new(
            Token::NL,
            state.line.text[state.line.pos..].to_string(),
            (state.line.num, state.line.pos),
            (state.line.num, state.line.pos + state.line.text[state.line.pos..].len()),
            state.line.text.to_string().clone(),
        ));
        state.line.pos = state.line.max;
        return Ok((LoopAction::None, stash));
    }

    if let Some(indent) = state.indents.last() {
        if col > *indent {
            state.indents.push(col);
            stash.push(TokInfo::new(
                Token::INDENT,
                state.line.text[..state.line.pos].to_string(),
                (state.line.num, 0),
                (state.line.num, state.line.pos),
                state.line.text.to_string().clone(),
            ));
        }
    }
    while state.indents.last().is_some() && col < *state.indents.last().unwrap() {
        if state.indents.contains(&col) {
            state.indents.pop();
            stash.push(TokInfo::new(
                Token::DEDENT,
                "".to_string(),
                (state.line.num, state.line.pos),
                (state.line.num, state.line.pos),
                state.line.text.to_string().clone(),
            ));
        } else {
            return Err(format!("unindent does not match any outer indentation level {}:{}", state.line.num, state.line.pos));
        }
    }

    return Ok((LoopAction::None, stash));
}

fn handle_string_start(state: &mut State, m: &Match) -> Option<Token> {
    let quote = m.sub_names["Quote"].as_str();
    let pattern = END_PATTERNS[quote];
    if m.text.to_ascii_lowercase().contains("f") {
        let pattern = choice(&[], Some(&[
            ("StartLBrace", START_LBRACE),
            ("End", pattern),
        ]));
        state.add_prog(m.end, m.end, pattern.as_str(), quote, Mode::Middle);
        return Some(Token::FstringStart);
    }
    state.add_prog(m.start, m.end, pattern, quote, Mode::Nil);
    return None;
}

fn handle_psuedo(state: &mut State, m: &Match) -> Option<Token> {
    match m.name.as_str() {
        "StringStart" => handle_string_start(state, m),
        "ws" => Some(Token::WS),
        "Comment" => Some(Token::Comment),
        "SearchPath" => Some(Token::SearchPath),
        "Name" => Some(Token::NAME),
        "Number" => Some(Token::NUMBER), // todo: or (token[0] == "." and token not in (".", "..."))
        "NL" => Some(if state.parenlev > 0 { Token::NL } else { Token::NEWLINE }),
        "Special" => {
            if "([{".contains(m.text.chars().last().unwrap()) {
                state.parenlev += 1;
            } else if [")", "]", "}"].contains(&m.text.as_str()) {
                if state.in_braces() && state.at_parenlev() {
                    let end = (state.line.num, m.end);
                    state.pop_prog().reset_prog(end);
                }
                state.parenlev -= 1;
            } else if m.text.as_str() == ":" && state.in_braces() && state.at_parenlev() {
                let pattern = choice(&[], Some(&[("RBrace", END_RBRACE)]));
                state.add_prog(m.start, m.end, pattern.as_str(), "", Mode::InColon);
            }
            Some(Token::OP)
        }
        "End" => {
            state.continued = true;
            None
        },
        _ => None,
    }
}

fn next_psuedo_matches(state: &mut State) -> Result<Option<TokInfo>, String> {
    if state.line.pos == state.line.max || state.in_fstring() {
        return Ok(None);
    }
    let m = state.match_pattern(PSEUDO_TOKENS.as_str());
    if m.is_none() {
        return Ok(None);
    }
    let m = m.unwrap();
    let token_type = handle_psuedo(state, &m);
    let (spos, epos) = ((state.line.num, m.start), (state.line.num, m.end));
    state.line.pos = m.end;

    if let Some(token_type) = token_type {
        let tok = TokInfo::new(token_type, m.text, spos, epos, state.line.text.clone());
        return Ok(Some(tok));
    }
    return Ok(None);
}

fn next_end_tokens(state: &State) -> Vec<TokInfo> {
    let mut tokens: Vec<TokInfo> = Vec::new();
    if let Some(last_line) = state.last_line.as_ref() {
        if !['\r', '\n'].contains(&last_line.text.chars().last().unwrap()) && !last_line.text.starts_with('#') {
            let token = TokInfo {
                typ: Token::NEWLINE,
                string: "".to_string(),
                start: (state.line.num - 1, last_line.text.len()),
                end: (state.line.num - 1, last_line.text.len() + 1),
                // line: "".to_string(),
            };
            tokens.push(token);
        }
    }
    tokens.extend(
        state.indents[1..].iter().map(|_| TokInfo {
            typ: Token::DEDENT,
            string: "".to_string(),
            start: (state.line.num, 0),
            end: (state.line.num, 0),
            // line: "".to_string(),
        })
    );

    tokens.push(TokInfo {
        typ: Token::ENDMARKER,
        string: "".to_string(),
        start: (state.line.num, 0),
        end: (state.line.num, 0),
        // line: "".to_string(),
    });
    return tokens;
}


fn handle_fstring_progs(state: &mut State) -> Vec<TokInfo> {
    let mut results = Vec::new();
    let endprog = state.end_progs.last().unwrap();
    if let Some(m) = state.match_pattern(&endprog.pattern) {
        if m.name == "End" { // quote match
            let middle_end = m.end - endprog.quote.len();
            let endquote = endprog.quote.to_string();
            if middle_end > state.line.pos || !endprog.text.is_empty() {
                results.push(state.prog_token(middle_end, Token::FstringMiddle));
            }
            results.push(TokInfo {
                typ: Token::FstringEnd,
                string: endquote, // Copy the quote string
                start: (state.line.num, state.line.pos),
                end: (state.line.num, m.end),
                // line: state.line.text.clone(),
            });
            state.pop_prog();
        } else { // "{" or "}"
            let middle_end = m.end - 1;
            if middle_end > state.line.pos || !endprog.text.is_empty() { // has buffer
                results.push(state.prog_token(middle_end, Token::FstringMiddle));
            }

            if m.name == "LBrace" {
                results.push(TokInfo {
                    typ: Token::OP,
                    string: "{".to_string(),
                    start: (state.line.num, state.line.pos),
                    end: (state.line.num, m.end),
                    // line: state.line.text.to_string(),
                });
                state.parenlev += 1;
                state.add_prog(m.end, m.end, "", "", Mode::InBraces(state.parenlev));
            } else { // rbrace
                results.push(TokInfo {
                    typ: Token::OP,
                    string: "}".to_string(),
                    start: (state.line.num, state.line.pos),
                    end: (state.line.num, m.end),
                    // line: state.line.text.to_string(),
                });
                state.parenlev -= 1;
                state.pop_prog(); // in-colon
                let end = (state.line.num, m.end);
                state.pop_prog().reset_prog(end); // in braces
            }
        }
        state.line.pos = m.end;
    }
    return results;
}

fn handle_end_progs<'a>(state: &mut State) -> Result<Vec<TokInfo>, String> {
    if state.end_progs.is_empty() {
        return Ok(vec![]);
    }
    if state.line.pos == 0 && state.line.text.is_empty() {
        let endprog = state.end_progs.last().unwrap();
        let (end_line, end_pos) = endprog.start;
        return Err(format!("EOF in multi-line string at {}:{} - {}:{}",
                           state.line.num,
                           state.line.pos, end_line, end_pos,
        ));
    }

    if state.in_braces() {
        return Ok(vec![]);
    }

    let mut results = Vec::new();
    if state.in_fstring() || state.in_colon() {
        if !state.end_progs.is_empty() {
            results.extend(handle_fstring_progs(state));
        }
    } else if let Some(endprog) = state.end_progs.last() {
        if let Some(m) = state.match_pattern(endprog.pattern.as_str()) {  // all on one line
            results.push(state.prog_token(m.end, Token::STRING));
            state.pop_prog();
            return Ok(results);
        }
    }

    // Check again if state changed and early return if so
    if state.in_braces() || state.end_progs.is_empty() {
        return Ok(results);
    }

    if (state.line.pos == 0 || state.in_multi_line_string() || state.in_continued_string()) && (state.end_progs.last().is_some()) {
        let endprog = state.end_progs.last_mut().unwrap();
        endprog.join_line(&state.line);
        state.line.pos = state.line.max;
    }
    return Ok(results);
}

struct Tokenizer<R: Read>
{
    stash: VecDeque<TokInfo>,  // Current line's tokens
    stopped: bool, // an error or \n has been encountered
    state: State,
    // an iterator over the lines in the stream
    reader: BufReader<R>,
}

impl<R: Read> Tokenizer<R> {
    fn new(lines: R) -> Self {
        Self {
            stash: VecDeque::new(),
            stopped: false,
            state: State::default(),
            reader: BufReader::new(lines),
        }
    }
}


impl<R: Read> Iterator for Tokenizer<R> {
    type Item = Result<TokInfo, String>; // The type of the values produced by the iterator

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(tok_info) = self.stash.pop_front() {
                return Some(Ok(tok_info));
            }
            if self.stopped {
                return None;
            }
            let mut current = String::new();

            if let Ok(read_bytes) = self.reader.read_line(&mut current) {
                if read_bytes == 0 { // EOF
                    self.stopped = true;
                    self.stash.extend(next_end_tokens(&self.state))
                } else {
                    let result = self.state.collect_for(current);
                    if let Ok(tokens) = result {
                        self.stash.extend(tokens);
                    } else {
                        self.stopped = true;
                        return Some(Err(result.unwrap_err()));
                    }
                }
            } else {
                return None;
            }
        }
    }
}


#[allow(unused)]
fn tokenize_file(path: &str) -> Tokenizer<File>
{
    let file = File::open(path).unwrap();
    Tokenizer::new(file)
}

fn tokenize_string(src: &str) -> Tokenizer<BufReader<Cursor<&[u8]>>> {
    let bytes = src.as_bytes();
    let cursor = Cursor::new(bytes);
    let reader = BufReader::new(cursor);
    Tokenizer::new(reader)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_next_psuedo_matches() {
        let mut state = State::default();
        state.set_line("a = 1".to_string());
        let result = next_psuedo_matches(&mut state);
        assert!(result.is_ok());
    }

    #[test]
    fn test_tokenizer() {
        let lines = "a = 1 \nif statement: 'string'";
        for token in tokenize_string(lines) {
            println!("{:?}", token);
        }
    }
}