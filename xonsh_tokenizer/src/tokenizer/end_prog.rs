use crate::regex::consts::Mode;
use crate::tokenizer::line_state::LineState;

#[derive(Debug, Clone)]
pub(crate) struct EndProg {
    pub(crate) pattern: String,
    pub(crate) text: String,
    pub(crate) contline: String,
    pub(crate) start: (usize, usize),
    pub(crate) quote: String,
    pub(crate) mode: Mode,
}


impl EndProg {
    pub fn new(
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

    pub(super) fn join(&mut self, line: &LineState, end: usize) {
        self.text += &line.text[line.pos..end];
    }

    pub(super) fn join_line(&mut self, line: &LineState) {
        self.text += &line.text[line.pos..];
        self.contline += &line.text;
    }

    pub(super) fn reset(&mut self, end: (usize, usize)) {
        self.start = end;
        self.text.clear();
        self.contline.clear();
    }
}