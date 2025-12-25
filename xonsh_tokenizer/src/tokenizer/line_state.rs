use crate::regex::consts::TABSIZE;
use crate::tokenizer::result::{LoopAction, LoopResult};
use crate::tokenizer::tok::{TokInfo, Token};

#[derive(Debug, Clone)]
pub(crate) struct LineState {
    pub(crate) text: String,
    pub(crate) num: usize, // line number
    pub(crate) pos: usize, // current position in line
    pub(crate) max: usize, // max position in line
    pub(crate) base_offset: usize,
}

impl Default for LineState {
    fn default() -> Self {
        Self::new("", 0, 0)
    }
}

impl LineState {
    pub(crate) fn new(line: &str, num: usize, base_offset: usize) -> Self {
        Self {
            text: line.to_string(),
            num,
            pos: 0,
            max: line.len(),
            base_offset,
        }
    }

    fn to_token<T: Into<Option<usize>>>(
        &self,
        tok: Token,
        string: &str,
        start: T,
        end: T,
    ) -> TokInfo {
        let start_idx = start.into().unwrap_or(self.pos);
        let end_idx = end.into().unwrap_or(self.pos + string.len());
        TokInfo::new(
            tok,
            (self.base_offset + start_idx, self.base_offset + end_idx),
            (self.num, start_idx),
            (self.num, end_idx),
        )
    }

    pub fn next_statement(&mut self, indents: &mut Vec<usize>) -> Result<LoopResult, String> {
        let mut stash: Vec<TokInfo> = Vec::new();
        if self.text.is_empty() {
            return Ok((LoopAction::Break, stash));
        }
        let mut col = 0;

        // measure leading whitespace
        while self.pos < self.max {
            match self.text.chars().nth(self.pos).unwrap() {
                ' ' => col += 1,
                '\t' => col = (col / TABSIZE + 1) * TABSIZE,
                '\u{C}' => col = 0, // form feed '\f'
                _ => break,
            }
            self.pos += 1;
        }
        if self.pos == self.max {
            return Ok((LoopAction::Break, stash));
        }

        let current_char = self.text.chars().nth(self.pos).unwrap();
        if "#\r\n".contains(current_char) {
            if current_char == '#' {
                let comment_token = self.text[self.pos..].trim_end_matches("\r\n");
                stash.push(self.to_token(Token::Comment, comment_token, None, None));
            }
            stash.push(self.to_token(Token::NL, &self.text[self.pos..], None, None));
            self.pos = self.max;
            return Ok((LoopAction::None, stash));
        }

        if let Some(indent) = indents.last() {
            if col > *indent {
                indents.push(col);
                stash.push(self.to_token(Token::INDENT, &self.text[..self.pos], 0, self.pos));
            }
        }
        while indents.last().is_some() && col < *indents.last().unwrap() {
            if indents.contains(&col) {
                indents.pop();
                stash.push(self.to_token(Token::DEDENT, "", self.pos, self.pos));
            } else {
                return Err(format!(
                    "unindent does not match any outer indentation level {}:{}",
                    self.num, self.pos
                ));
            }
        }

        return Ok((LoopAction::None, stash));
    }
}
