use winnow::error::{ErrMode, ErrorKind, ParserError};
use winnow::prelude::*;
use winnow::stream::Stream;
use winnow::token::take_while;
use winnow::combinator::trace;

fn parse_prefix<'s>(input: &mut &'s str) -> PResult<&'s str> {
    "0x".parse_next(input)
}

fn parse_digits<'s>(input: &mut &'s str) -> PResult<&'s str> {
    take_while(1.., (('0'..='9'), ('A'..='F'), ('a'..='f'))).parse_next(input)
}

pub fn parser<'s>(input: &mut &'s str) -> PResult<char> {
    let c = input
        .next_token()
        .ok_or_else(|| ErrMode::from_error_kind(input, ErrorKind::Token))?;
    if c != 'H' {
        return Err(ErrMode::from_error_kind(input, ErrorKind::Verify));
    }
    Ok(c)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_one() {
        let mut input = "0x1a2b Hello";
        let parser = (parse_prefix, parse_digits);
        let (prefix, digits) = trace("parse hex digits", parser).parse_next(&mut input).unwrap();

        assert_eq!(prefix, "0x");
        assert_eq!(digits, "1a2b");
        assert_eq!(input, " Hello");
    }
}
