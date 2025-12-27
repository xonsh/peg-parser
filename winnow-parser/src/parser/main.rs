use winnow::combinator::trace;
use winnow::error::ErrMode;
use winnow::prelude::*;
use winnow::token::take_while;

fn parse_prefix<'s>(input: &mut &'s str) -> ModalResult<&'s str> {
    "0x".parse_next(input)
}

fn parse_digits<'s>(input: &mut &'s str) -> ModalResult<&'s str> {
    take_while(1.., (('0'..='9'), ('A'..='F'), ('a'..='f'))).parse_next(input)
}

pub fn parser<'s>(input: &mut &'s str) -> ModalResult<char> {
    let c = input
        .chars()
        .next()
        .ok_or_else(|| ErrMode::Backtrack(winnow::error::ContextError::new()))?;
    if c != 'H' {
        *input = &input[c.len_utf8()..];
        return Ok(c);
    }
    Err(ErrMode::Backtrack(winnow::error::ContextError::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_one() {
        let mut input = "0x1a2b Hello";
        let parser = (parse_prefix, parse_digits);
        let (prefix, digits) = trace("parse hex digits", parser)
            .parse_next(&mut input)
            .unwrap();

        assert_eq!(prefix, "0x");
        assert_eq!(digits, "1a2b");
        assert_eq!(input, " Hello");
    }
}
