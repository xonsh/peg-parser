use std::collections::HashMap;
use std::fmt::Debug;
use std::iter::Iterator;
use std::mem::{discriminant, Discriminant};

use crate::regex::consts::{Mode, END_PATTERNS, END_RBRACE, PSEUDO_TOKENS, START_LBRACE};
use crate::regex::fns::{choice, compile};
use crate::tokenizer::end_prog::EndProg;
use crate::tokenizer::line_state::LineState;
use crate::tokenizer::result::LoopAction;
use crate::tokenizer::tok::{TokInfo, Token};

#[derive(Debug)]
pub(crate) struct Match {
    // overall match
    pub(crate) start: usize,
    pub(crate) end: usize,
    pub(crate) name: String, // name of the pattern matched
    pub(crate) text: String,
    // group names in this match
    pub(crate) sub_names: HashMap<String, String>,
}

#[derive(Debug)]
pub(crate) struct State {
    pub(crate) parenlev: usize,
    pub(crate) continued: bool,
    pub(crate) indents: Vec<usize>,
    pub(crate) last_line: Option<LineState>,
    pub(crate) line: LineState,
    pub(crate) end_progs: Vec<EndProg>,
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
    pub(crate) fn set_line(&mut self, line: String) {
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
            line: endprog.contline.clone(),
        };
    }

    fn match_pattern(&self, pattern: &str) -> Option<Match> {
        let re = compile(pattern);
        let captures = re.captures(&self.line.text[self.line.pos..]).ok()??;
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
        Some(Match {
            start: m.start() + self.line.pos,
            end: m.end() + self.line.pos,
            name: first_name,
            text: m.as_str().to_string(),
            sub_names: matches,
        })
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
        return self
            .end_progs
            .last()
            .map(|m| m.quote.len() == 3)
            .unwrap_or(false);
    }

    fn in_continued_string(&self) -> bool {
        return self.end_progs.last().is_some()
            && (self.line.text.ends_with("\\\n") || self.line.text.ends_with("\\\r\n"));
    }
    fn collect_until(&mut self) -> Result<Vec<TokInfo>, String> {
        let mut pos = self.line.pos;
        let mut results = Vec::new();
        while self.line.pos < self.line.max {
            let res = self.handle_end_progs()?;
            results.extend(res);

            if let Some(t) = self.next_psuedo_matches()? {
                results.push(t);
            } else if pos == self.line.pos {
                pos = self.line.pos + 1;
                results.push(TokInfo {
                    typ: Token::ErrorToken,
                    string: self.line.text[self.line.pos..pos].to_string(),
                    start: (self.line.num, self.line.pos),
                    end: (self.line.num, pos),
                    line: self.line.text.to_string(),
                });
                self.line.pos = pos;
            }
            // else {return Err(format!("Invalid tokenizer state at {}:{}", self.line.num, self.line.pos));}
        }
        return Ok(results);
    }
    pub(crate) fn collect_for(&mut self, line: String) -> Result<Vec<TokInfo>, String> {
        self.set_line(line);
        let mut results = Vec::new();

        if !self.end_progs.is_empty() {
            let res = self.handle_end_progs()?;
            results.extend(res);
        } else if self.parenlev == 0 && !self.continued {
            match self.line.next_statement(&mut self.indents)? {
                (LoopAction::Break, res) => {
                    results.extend(res);
                    return Ok(results);
                }
                (_, res) => {
                    results.extend(res);
                }
            }
        } else {
            // continued statement
            if self.line.text.is_empty() {
                return Err(format!(
                    "EOF in multi-line statement {}:{}",
                    self.line.num, self.line.pos
                ));
            }
            self.continued = false;
        }
        let res = self.collect_until()?; // store in a variable to debug
        results.extend(res);
        Ok(results)
    }
    fn handle_string_start(&mut self, m: &Match) -> Option<Token> {
        let quote = m.sub_names["Quote"].as_str();
        let pattern = END_PATTERNS[quote];
        if m.text.to_ascii_lowercase().contains("f") {
            let pattern = choice(&[], Some(&[("LBrace", START_LBRACE), ("End", pattern)]));
            self.add_prog(m.end, m.end, pattern.as_str(), quote, Mode::Middle);
            return Some(Token::FstringStart);
        }
        self.add_prog(m.start, m.end, pattern, quote, Mode::Nil);
        return None;
    }

    fn handle_psuedo(&mut self, m: &Match) -> Option<Token> {
        match m.name.as_str() {
            "StringStart" => self.handle_string_start(m),
            "ws" => Some(Token::WS),
            "Comment" => Some(Token::Comment),
            "SearchPath" => Some(Token::SearchPath),
            "Name" => Some(Token::NAME),
            "Number" => Some(Token::NUMBER), // todo: or (token[0] == "." and token not in (".", "..."))
            "NL" => Some(if self.parenlev > 0 {
                Token::NL
            } else {
                Token::NEWLINE
            }),
            "Special" => {
                if "([{".contains(m.text.chars().last().unwrap()) {
                    self.parenlev += 1;
                } else if [")", "]", "}"].contains(&m.text.as_str()) {
                    if self.in_braces() && self.at_parenlev() {
                        let end = (self.line.num, m.end);
                        self.pop_prog().reset_prog(end);
                    }
                    self.parenlev -= 1;
                } else if m.text.as_str() == ":" && self.in_braces() && self.at_parenlev() {
                    let pattern = choice(&[], Some(&[("RBrace", END_RBRACE)]));
                    self.add_prog(m.start + 1, m.end, pattern.as_str(), "", Mode::InColon);
                }
                Some(Token::OP)
            }
            "End" => {
                self.continued = true;
                None
            }
            _ => None,
        }
    }
    fn next_psuedo_matches(&mut self) -> Result<Option<TokInfo>, String> {
        if self.line.pos == self.line.max || self.in_fstring() {
            return Ok(None);
        }
        let m = self.match_pattern(PSEUDO_TOKENS.as_str());
        if m.is_none() {
            return Ok(None);
        }
        let m = m.unwrap();
        let token_type = self.handle_psuedo(&m);
        let (spos, epos) = ((self.line.num, m.start), (self.line.num, m.end));
        self.line.pos = m.end;

        if let Some(token_type) = token_type {
            let tok = TokInfo::new(token_type, m.text, spos, epos, self.line.text.clone());
            return Ok(Some(tok));
        }
        return Ok(None);
    }

    pub(crate) fn next_end_tokens(&self) -> Vec<TokInfo> {
        let mut tokens: Vec<TokInfo> = Vec::new();
        if let Some(last_line) = self.last_line.as_ref() {
            if !['\r', '\n'].contains(&last_line.text.chars().last().unwrap())
                && !last_line.text.starts_with('#')
            {
                let token = TokInfo {
                    typ: Token::NEWLINE,
                    string: "".to_string(),
                    start: (last_line.num - 1, last_line.text.len()),
                    end: (last_line.num - 1, last_line.text.len() + 1),
                    line: "".to_string(),
                };
                tokens.push(token);
            }
        }
        tokens.extend(self.indents[1..].iter().map(|_| TokInfo {
            typ: Token::DEDENT,
            string: "".to_string(),
            start: (self.line.num, 0),
            end: (self.line.num, 0),
            line: "".to_string(),
        }));

        tokens.push(TokInfo {
            typ: Token::ENDMARKER,
            string: "".to_string(),
            start: (self.line.num, 0),
            end: (self.line.num, 0),
            line: "".to_string(),
        });
        return tokens;
    }

    fn handle_fstring_progs(&mut self) -> Vec<TokInfo> {
        let mut results = Vec::new();
        let endprog = self.end_progs.last().unwrap();
        if let Some(m) = self.match_pattern(&endprog.pattern) {
            if m.name == "End" {
                // quote match
                let middle_end = m.end - endprog.quote.len();
                let endquote = endprog.quote.to_string();
                if middle_end > self.line.pos || !endprog.text.is_empty() {
                    results.push(self.prog_token(middle_end, Token::FstringMiddle));
                }
                results.push(TokInfo {
                    typ: Token::FstringEnd,
                    string: endquote, // Copy the quote string
                    start: (self.line.num, self.line.pos),
                    end: (self.line.num, m.end),
                    line: self.line.text.clone(),
                });
                self.pop_prog();
            } else {
                // "{" or "}"
                let middle_end = m.end - 1;
                if middle_end > self.line.pos || !endprog.text.is_empty() {
                    // has buffer
                    results.push(self.prog_token(middle_end, Token::FstringMiddle));
                }
                match m.name.as_str() {
                    "LBrace" => {
                        results.push(TokInfo {
                            typ: Token::OP,
                            string: "{".to_string(),
                            start: (self.line.num, self.line.pos),
                            end: (self.line.num, m.end),
                            line: self.line.text.to_string(),
                        });
                        self.parenlev += 1;
                        self.add_prog(m.end, m.end, "", "", Mode::InBraces(self.parenlev));
                    }
                    "RBrace" => {
                        results.push(TokInfo {
                            typ: Token::OP,
                            string: "}".to_string(),
                            start: (self.line.num, self.line.pos),
                            end: (self.line.num, m.end),
                            line: self.line.text.to_string(),
                        });
                        self.parenlev -= 1;
                        self.pop_prog(); // in-colon
                        let end = (self.line.num, m.end);
                        self.pop_prog().reset_prog(end); // in braces
                    }
                    _ => panic!("Unmatched regex at {}:{}", self.line.num, self.line.pos),
                }
            }
            self.line.pos = m.end;
        }
        return results;
    }

    fn handle_end_progs<'a>(&mut self) -> Result<Vec<TokInfo>, String> {
        if self.end_progs.is_empty() {
            return Ok(vec![]);
        }
        if self.line.pos == 0 && self.line.text.is_empty() {
            let endprog = self.end_progs.last().unwrap();
            let (end_line, end_pos) = endprog.start;
            return Err(format!(
                "EOF in multi-line string at {}:{} - {}:{}",
                self.line.num, self.line.pos, end_line, end_pos,
            ));
        }

        if self.in_braces() {
            return Ok(vec![]);
        }

        let mut results = Vec::new();
        if self.in_fstring() || self.in_colon() {
            if !self.end_progs.is_empty() {
                results.extend(self.handle_fstring_progs());
            }
        } else if let Some(endprog) = self.end_progs.last() {
            if let Some(m) = self.match_pattern(endprog.pattern.as_str()) {
                // all on one line
                results.push(self.prog_token(m.end, Token::STRING));
                self.pop_prog();
                return Ok(results);
            }
        }

        // Check again if state changed and early return if so
        if self.in_braces() || self.end_progs.is_empty() {
            return Ok(results);
        }

        if (self.line.pos == 0 || self.in_multi_line_string() || self.in_continued_string())
            && (self.end_progs.last().is_some())
        {
            let endprog = self.end_progs.last_mut().unwrap();
            endprog.join_line(&self.line);
            self.line.pos = self.line.max;
        }
        return Ok(results);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_next_psuedo_matches() {
        let mut state = State::default();
        state.set_line("a = 1".to_string());
        let result = state.next_psuedo_matches();
        assert!(result.is_ok());
    }
}
