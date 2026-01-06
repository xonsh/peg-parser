use crate::result::{Error, Result};
use crate::{range::RangeArgument, set::Set};
use std::{
    fmt::{Debug, Display},
    ops::Bound::{Excluded, Included, Unbounded},
    ops::{Add, BitOr, Mul, Neg, Not, Shr, Sub},
};

type Parse<'a, I, O> = dyn Fn(&'a [I], usize) -> Result<(O, usize)> + 'a;

/// Parser combinator.
pub struct Parser<'a, I, O> {
    pub method: Box<Parse<'a, I, O>>,
}

impl<'a, I, O> Parser<'a, I, O> {
    /// Create new parser.
    pub fn new<P>(parse: P) -> Self
    where
        P: Fn(&'a [I], usize) -> Result<(O, usize)> + 'a,
    {
        Self {
            method: Box::new(parse),
        }
    }

    /// Apply the parser to parse input.
    pub fn parse(&self, input: &'a [I]) -> Result<O> {
        (self.method)(input, 0).map(|(out, _)| out)
    }

    /// Parse input at specified position.
    pub fn parse_at(&self, input: &'a [I], start: usize) -> Result<(O, usize)> {
        (self.method)(input, start)
    }

    /// Convert parser result to desired value.
    pub fn map<U, F>(self, f: F) -> Parser<'a, I, U>
    where
        F: Fn(O) -> U + 'a,
        I: 'a,
        O: 'a,
        U: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).map(|(out, pos)| (f(out), pos))
        })
    }

    /// Convert parser result to desired value, fail in case of conversion error.
    pub fn convert<U, E, F>(self, f: F) -> Parser<'a, I, U>
    where
        F: Fn(O) -> ::std::result::Result<U, E> + 'a,
        E: Debug,
        O: 'a,
        U: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).and_then(|(res, pos)| match f(res) {
                Ok(out) => Ok((out, pos)),
                Err(err) => Err(Error::Conversion {
                    message: format!("Conversion error: {:?}", err),
                    position: start,
                }),
            })
        })
    }

    /// Cache parser output result to speed up backtracking.
    pub fn cache(self) -> Self
    where
        O: Clone + 'a,
    {
        use std::{cell::RefCell, collections::HashMap};
        let results = RefCell::new(HashMap::new());
        Self::new(move |input: &'a [I], start: usize| {
            let key = (start, format!("{:p}", &self.method));
            results
                .borrow_mut()
                .entry(key)
                .or_insert_with(|| (self.method)(input, start))
                .clone()
        })
    }

    /// Get input position after matching parser.
    pub fn pos(self) -> Parser<'a, I, usize>
    where
        O: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).map(|(_, pos)| (pos, pos))
        })
    }

    /// Collect all matched input symbols.
    pub fn collect(self) -> Parser<'a, I, &'a [I]>
    where
        O: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).map(|(_, end)| (&input[start..end], end))
        })
    }

    /// Discard parser output.
    pub fn discard(self) -> Parser<'a, I, ()>
    where
        O: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).map(|(_, end)| ((), end))
        })
    }

    /// Make parser optional.
    pub fn opt(self) -> Parser<'a, I, Option<O>>
    where
        O: 'a,
    {
        Parser::new(
            move |input: &'a [I], start: usize| match (self.method)(input, start) {
                Ok((out, pos)) => Ok((Some(out), pos)),
                Err(_) => Ok((None, start)),
            },
        )
    }

    /// `p.repeat(5)` repeat p exactly 5 times
    /// `p.repeat(0..)` repeat p zero or more times
    /// `p.repeat(1..)` repeat p one or more times
    /// `p.repeat(1..4)` match p at least 1 and at most 3 times
    pub fn repeat<R>(self, range: R) -> Parser<'a, I, Vec<O>>
    where
        R: RangeArgument<usize> + Debug + 'a,
        O: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            let mut items = vec![];
            let mut pos = start;
            loop {
                match range.end() {
                    Included(&max_count) => {
                        if items.len() >= max_count {
                            break;
                        }
                    }
                    Excluded(&max_count) => {
                        if items.len() + 1 >= max_count {
                            break;
                        }
                    }
                    Unbounded => (),
                }

                let Ok((item, item_pos)) = (self.method)(input, pos) else {
                    break;
                };
                items.push(item);
                pos = item_pos;
            }
            if let Included(&min_count) = range.start() {
                if items.len() < min_count {
                    return Err(Error::Mismatch {
                        message: format!(
                            "expect repeat at least {} times, found {} times",
                            min_count,
                            items.len()
                        ),
                        position: start,
                    });
                }
            }
            Ok((items, pos))
        })
    }

    #[cfg(not(feature = "trace"))]
    /// Give parser a name to identify parsing errors.
    pub fn name(self, name: &'a str) -> Self
    where
        O: 'a,
    {
        Parser::new(
            move |input: &'a [I], start: usize| match (self.method)(input, start) {
                res @ Ok(_) => res,
                Err(err) => match err {
                    Error::Custom { .. } => Err(err),
                    _ => Err(Error::Custom {
                        message: format!("failed to parse {}", name),
                        position: start,
                        inner: Some(Box::new(err)),
                    }),
                },
            },
        )
    }

    #[cfg(feature = "trace")]
    /// Trace parser calls and results. Similar to name
    pub fn name(self, name: &'a str) -> Self
    where
        O: 'a,
    {
        Parser::new(move |input: &'a [I], start: usize| {
            eprintln!("parse: {} ({})", name, start);
            match (self.method)(input, start) {
                res @ Ok(_) => {
                    eprintln!("       {} ({}): ok", name, start);
                    res
                }
                Err(err) => {
                    eprintln!("       {} ({}): error", name, start);
                    match err {
                        Error::Custom { .. } => Err(err),
                        _ => Err(Error::Custom {
                            message: format!("failed to parse {}", name),
                            position: start,
                            inner: Some(Box::new(err)),
                        }),
                    }
                }
            }
        })
    }

    /// Mark parser as expected, abort early when failed in ordered choice.
    pub fn expect(self, name: &'a str) -> Self
    where
        O: 'a,
    {
        Parser::new(
            move |input: &'a [I], start: usize| match (self.method)(input, start) {
                res @ Ok(_) => res,
                Err(err) => Err(Error::Expect {
                    message: format!("Expect {}", name),
                    position: start,
                    inner: Box::new(err),
                }),
            },
        )
    }
}

/// Always succeeds, consume no input.
pub fn empty<'a, I>() -> Parser<'a, I, ()> {
    Parser::new(|_: &[I], start: usize| Ok(((), start)))
}

/// Match any symbol.
pub fn any<'a, I>() -> Parser<'a, I, I>
where
    I: Clone,
{
    Parser::new(|input: &[I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Mismatch {
                message: "end of input reached".to_owned(),
                position: start,
            });
        };
        Ok((s.clone(), start + 1))
    })
}

/// Success when current input symbol equals `t`.
pub fn sym<'a, I>(t: I) -> Parser<'a, I, I>
where
    I: Clone + PartialEq + Display,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Incomplete);
        };
        if t != *s {
            return Err(Error::Mismatch {
                message: format!("expect: {}, found: {}", t, s),
                position: start,
            });
        }
        Ok((s.clone(), start + 1))
    })
}

/// Success when sequence of symbols matches current input.
pub fn seq<'a, 'b: 'a, I>(tag: &'b [I]) -> Parser<'a, I, &'a [I]>
where
    I: PartialEq + Debug,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let mut index = 0;
        loop {
            let pos = start + index;
            if index == tag.len() {
                return Ok((tag, pos));
            }
            let Some(s) = input.get(pos) else {
                return Err(Error::Incomplete);
            };
            if tag[index] != *s {
                return Err(Error::Mismatch {
                    message: format!("seq {:?} expect: {:?}, found: {:?}", tag, tag[index], s),
                    position: pos,
                });
            }
            index += 1;
        }
    })
}

/// Success when tag matches current input.
pub fn tag<'a, 'b: 'a>(tag: &'b str) -> Parser<'a, char, &'a str> {
    Parser::new(move |input: &'a [char], start: usize| {
        let mut pos = start;
        for c in tag.chars() {
            let Some(&s) = input.get(pos) else {
                return Err(Error::Incomplete);
            };
            if c != s {
                return Err(Error::Mismatch {
                    message: format!("tag {:?} expect: {:?}, found: {}", tag, c, s),
                    position: pos,
                });
            }
            pos += 1;
        }
        Ok((tag, pos))
    })
}

/// Parse separated list.
pub fn list<'a, I, O, U>(
    parser: Parser<'a, I, O>,
    separator: Parser<'a, I, U>,
) -> Parser<'a, I, Vec<O>>
where
    O: 'a,
    U: 'a,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let mut items = vec![];
        let mut pos = start;
        if let Ok((first_item, first_pos)) = (parser.method)(input, pos) {
            items.push(first_item);
            pos = first_pos;
            while let Ok((_, sep_pos)) = (separator.method)(input, pos) {
                match (parser.method)(input, sep_pos) {
                    Ok((more_item, more_pos)) => {
                        items.push(more_item);
                        pos = more_pos;
                    }
                    Err(_) => break,
                }
            }
        }
        Ok((items, pos))
    })
}

/// Success when current input symbol is one of the set.
pub fn one_of<'a, I, S>(set: &'a S) -> Parser<'a, I, I>
where
    I: Clone + PartialEq + Display + Debug,
    S: Set<I> + ?Sized,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Incomplete);
        };
        if !set.contains(s) {
            return Err(Error::Mismatch {
                message: format!("expect one of: {}, found: {}", set.to_str(), s),
                position: start,
            });
        };
        Ok((s.clone(), start + 1))
    })
}

/// Success when current input symbol is none of the set.
pub fn none_of<'a, I, S>(set: &'static S) -> Parser<'a, I, I>
where
    I: Clone + PartialEq + Display + Debug,
    S: Set<I> + ?Sized,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Incomplete);
        };
        if set.contains(s) {
            return Err(Error::Mismatch {
                message: format!("expect none of: {}, found: {}", set.to_str(), s),
                position: start,
            });
        }
        Ok((s.clone(), start + 1))
    })
}

/// Success when predicate returns true on current input symbol.
pub fn is_a<'a, I, F>(predicate: F) -> Parser<'a, I, I>
where
    I: Clone + PartialEq + Display + Debug,
    F: Fn(I) -> bool + 'a,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Incomplete);
        };
        if !predicate(s.clone()) {
            return Err(Error::Mismatch {
                message: format!("is_a predicate failed on: {}", s),
                position: start,
            });
        }
        Ok((s.clone(), start + 1))
    })
}

/// Success when predicate returns false on current input symbol.
pub fn not_a<'a, I, F>(predicate: F) -> Parser<'a, I, I>
where
    I: Clone + PartialEq + Display + Debug,
    F: Fn(I) -> bool + 'a,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let Some(s) = input.get(start) else {
            return Err(Error::Incomplete);
        };
        if predicate(s.clone()) {
            return Err(Error::Mismatch {
                message: format!("not_a predicate failed on: {}", s),
                position: start,
            });
        }
        Ok((s.clone(), start + 1))
    })
}

/// Read n symbols.
pub fn take<'a, I>(n: usize) -> Parser<'a, I, &'a [I]> {
    Parser::new(move |input: &'a [I], start: usize| {
        let pos = start + n;
        if input.len() < pos {
            return Err(Error::Incomplete);
        }
        Ok((&input[start..pos], pos))
    })
}

/// Skip n symbols.
pub fn skip<'a, I>(n: usize) -> Parser<'a, I, ()> {
    Parser::new(move |input: &'a [I], start: usize| {
        let pos = start + n;
        if input.len() < pos {
            return Err(Error::Incomplete);
        }
        Ok(((), pos))
    })
}

/// Call a parser factory, can be used to create recursive parsers.
pub fn call<'a, I, O, F>(parser_factory: F) -> Parser<'a, I, O>
where
    O: 'a,
    F: Fn() -> Parser<'a, I, O> + 'a,
{
    Parser::new(move |input: &'a [I], start: usize| {
        let parser = parser_factory();
        (parser.method)(input, start)
    })
}

/// Success when end of input is reached.
pub fn end<'a, I>() -> Parser<'a, I, ()>
where
    I: Display,
{
    Parser::new(|input: &'a [I], start: usize| {
        if let Some(s) = input.get(start) {
            return Err(Error::Mismatch {
                message: format!("expect end of input, found: {}", s),
                position: start,
            });
        }
        Ok(((), start))
    })
}

/// Sequence reserve value
impl<'a, I, O: 'a, U: 'a> Add<Parser<'a, I, U>> for Parser<'a, I, O> {
    type Output = Parser<'a, I, (O, U)>;

    fn add(self, other: Parser<'a, I, U>) -> Self::Output {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).and_then(|(out1, pos1)| {
                (other.method)(input, pos1).map(|(out2, pos2)| ((out1, out2), pos2))
            })
        })
    }
}

/// Sequence discard second value
impl<'a, I, O: 'a, U: 'a> Sub<Parser<'a, I, U>> for Parser<'a, I, O> {
    type Output = Parser<'a, I, O>;

    fn sub(self, other: Parser<'a, I, U>) -> Self::Output {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start)
                .and_then(|(out1, pos1)| (other.method)(input, pos1).map(|(_, pos2)| (out1, pos2)))
        })
    }
}

/// Sequence discard first value
impl<'a, I: 'a, O: 'a, U: 'a> Mul<Parser<'a, I, U>> for Parser<'a, I, O> {
    type Output = Parser<'a, I, U>;

    fn mul(self, other: Parser<'a, I, U>) -> Self::Output {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).and_then(|(_, pos1)| (other.method)(input, pos1))
        })
    }
}

/// Chain two parsers where the second parser depends on the first's result.
impl<'a, I, O: 'a, U: 'a, F: Fn(O) -> Parser<'a, I, U> + 'a> Shr<F> for Parser<'a, I, O> {
    type Output = Parser<'a, I, U>;

    fn shr(self, other: F) -> Self::Output {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).and_then(|(out, pos)| (other(out).method)(input, pos))
        })
    }
}

/// Ordered choice
impl<'a, I, O: 'a> BitOr for Parser<'a, I, O> {
    type Output = Parser<'a, I, O>;

    fn bitor(self, other: Parser<'a, I, O>) -> Self::Output {
        Parser::new(
            move |input: &'a [I], start: usize| match (self.method)(input, start) {
                Ok(out) => Ok(out),
                Err(err) => match err {
                    Error::Expect { .. } => Err(err),
                    _ => (other.method)(input, start),
                },
            },
        )
    }
}

/// And predicate
impl<'a, I, O: 'a> Neg for Parser<'a, I, O> {
    type Output = Parser<'a, I, bool>;

    fn neg(self) -> Self::Output {
        Parser::new(move |input: &'a [I], start: usize| {
            (self.method)(input, start).map(|_| (true, start))
        })
    }
}

/// Not predicate
impl<'a, I, O: 'a> Not for Parser<'a, I, O> {
    type Output = Parser<'a, I, bool>;

    fn not(self) -> Self::Output {
        Parser::new(
            move |input: &'a [I], start: usize| match (self.method)(input, start) {
                Ok(_) => Err(Error::Mismatch {
                    message: "not predicate failed".to_string(),
                    position: start,
                }),
                Err(_) => Ok((true, start)),
            },
        )
    }
}
