use std::collections::VecDeque;
use std::fs::File;
use std::io::{BufRead, BufReader, Cursor, Read};
use std::iter::Iterator;

use crate::tokenizer::state::State;
use crate::tokenizer::tok::TokInfo;

pub struct Tokenizer<R: Read> {
    stash: VecDeque<TokInfo>, // Current line's tokens
    stopped: bool,            // an error or \n has been encountered
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
                if read_bytes == 0 {
                    // EOF
                    self.stopped = true;
                    self.state.set_line("".to_string());
                    let res = self.state.next_end_tokens();
                    self.stash.extend(res);
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
pub fn tokenize_file(path: &str) -> Result<Tokenizer<File>, std::io::Error> {
    let file = File::open(path)?;
    Ok(Tokenizer::new(file))
}

pub fn tokenize_string(src: &str) -> Tokenizer<BufReader<Cursor<&[u8]>>> {
    let bytes = src.as_bytes();
    let cursor = Cursor::new(bytes);
    let reader = BufReader::new(cursor);
    Tokenizer::new(reader)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn handle_test_case(lines: &str, expected: &Vec<&str>) -> Result<(), String> {
        let result = tokenize_string(lines)
            .map(|x| x.unwrap())
            .map(|x| format!("{:?}({}){}", x.typ, x.string, x.start.1))
            .collect::<Vec<_>>();
        assert_eq!(&result, expected);
        Ok(())
    }

    #[test]
    fn test_tokenizer() -> Result<(), String> {
        [
            (
                "a = 1 \nif statement: 'string'",
                vec![
                    "NAME(a)0",
                    "WS( )1",
                    "OP(=)2",
                    "WS( )3",
                    "NUMBER(1)4",
                    "WS( )5",
                    "NEWLINE(\n)6",
                    "NAME(if)0",
                    "WS( )2",
                    "NAME(statement)3",
                    "OP(:)12",
                    "WS( )13",
                    "STRING('string')14",
                    "NEWLINE()22",
                    "ENDMARKER()0",
                ],
            ),
            (
                r#"a = f"{d}" "rr""#,
                vec![
                    "NAME(a)0",
                    "WS( )1",
                    "OP(=)2",
                    "WS( )3",
                    "FstringStart(f\")4",
                    "OP({)6",
                    "NAME(d)7",
                    "OP(})8",
                    "FstringEnd(\")9",
                    "WS( )10",
                    "STRING(\"rr\")11",
                    "NEWLINE()15",
                    "ENDMARKER()0",
                ],
            ),
            (
                "f'{expr::}'",
                vec![
                    "FstringStart(f')0",
                    "OP({)2",
                    "NAME(expr)3",
                    "OP(:)7",
                    "FstringMiddle(:)8",
                    "OP(})9",
                    "FstringEnd(')10",
                    "NEWLINE()11",
                    "ENDMARKER()0",
                ],
            ),
        ]
        .iter()
        .try_for_each(|(a, b)| handle_test_case(a, b))?;

        Ok(())
    }
}
