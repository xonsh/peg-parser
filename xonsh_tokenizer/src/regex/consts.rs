use std::collections::HashMap;
use once_cell::sync::Lazy;
use regex::escape;
use crate::regex::fns::*;

pub const OPERATORS: [&str; 60] = [
    "!=", "%", "%=", "&", "&=", "(", ")", "*", "**", "**=", "*=", "+", "+=", ",", "-", "-=", "->",
    ".", "...", "/", "//", "//=", "/=", ":", ":=", ";", "<", "<<", "<<=", "<=", "=", "==", ">",
    ">=", ">>", ">>=", "@", "@=", "[", "]", "^", "^=", "{", "|", "|=", "}", "~", "!", "$", "?",
    "??", "||", "&&", "@(", "!(", "![", "$(", "$[", "${", "@$(",
];

pub static STRING_START: Lazy<String> = Lazy::new(|| {
    let prefix = group(
        &all_string_prefixes(), Some("StringPrefix".to_string()), None,
    );
    let triple_quote = group(&["'''", "\"\"\""], Some("TripleQt"), None);
    let single_quote = group(&["\"", "'"], Some("SingleQt"), None);
    let quote = group(&[triple_quote, single_quote], Some("Quote".to_string()), None);
    return prefix + &quote;
});


pub static WHITESPACE: &str = r"[ \f\t]+";
pub static COMMENT: &str = r"#[^\r\n]*";
pub static NAME: &str = r"\w+";

pub static NUMBER: Lazy<String> = Lazy::new(|| {
    let hex = r"0[xX](?:_?[0-9a-fA-F])+";
    let bin = r"0[bB](?:_?[01])+";
    let oct = r"0[oO](?:_?[0-7])+";
    let dec = r"(?:0(?:_?0)*|[1-9](?:_?[0-9])*)";
    let int_number = group(&[hex, bin, oct, dec], None, None);

    let exp = r"[eE][-+]?[0-9](?:_?[0-9])*";
    let pointfloat = group(&[r"[0-9](?:_?[0-9])*\.(?:[0-9](?:_?[0-9])*)?", r"\.[0-9](?:_?[0-9])*"], None, None) + maybe(&[exp]).as_str();
    let expfloat = r"[0-9](?:_?[0-9])*".to_owned() + exp;
    let float_number = group(&[&pointfloat, &expfloat], None, None);
    let imag_number = group(&[r"[0-9](?:_?[0-9])*[jJ]", (float_number.clone() + r"[jJ]").as_str()], None, None);
    return group(&[&imag_number, &float_number, &int_number], None, None);
});

pub static OPS: Lazy<String> = Lazy::new(|| {
    // sort the operators in reverse order
    let mut ops = Vec::from(OPERATORS);
    ops.sort();
    ops.reverse();
    // regex.escape
    let alts = ops.iter().map(|s| {
        if s.starts_with("&") || s.starts_with("~") {
            s.to_string()
        } else {
            escape(s)
        }
    }).collect::<Vec<String>>();
    return group(&alts, Some("Operator".to_string()), None);
});


pub static PSEUDO_TOKENS: Lazy<String> = Lazy::new(|| {
    return choice(
        &[],
        Some(&[
            ("Comment", COMMENT),
            ("StringStart", STRING_START.as_str()),
            ("End", r"\\\r?\n"), // |\Z is removed
            ("NL", r"\r?\n"),
            ("SearchPath", r"([rgpf]+|@\w*)?`([^\n`\\]*(?:\\.[^\n`\\]*)*)`"),
            ("Number", NUMBER.as_str()),
            ("Special", OPS.as_str()),
            ("Name", NAME),
            ("ws", WHITESPACE),
        ]),
    );
});

pub static END_PATTERNS: Lazy<HashMap<&str, &str>> = Lazy::new(|| {
    HashMap::from([
        ("'", r"(?:[^'\\]|\\.)*'"),
        ("\"", r#"(?:[^"\\]|\\.)*""#),
        ("'''", r"(?:[^'\\]|\\.|'(?!''))*'''"),
        (r#"""""#, r#"(?:[^"\\]|\\.|"(?!""))*""""#),
    ])
});

pub static START_LBRACE: &str = r".*?(?=\{(?!\{)){";
pub static END_RBRACE: &str = r".*?(?=\}(?!\}))}";

pub static TABSIZE: usize = 8;

#[derive(Debug, Clone, PartialEq)]
pub enum Mode {
    /// in the string portion of an f-string (outside braces)
    Middle,
    /// in the format specifier ({:*})
    InColon,
    /// in the format specifier ({})
    InBraces(usize),
    Nil,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_start() {
        assert_eq!(STRING_START.as_str(), "(?P<StringPrefix>(|B|BR|Br|F|FP|FR|Fp|Fr|P|PF|PR|Pf|Pr|R|RB|RF|RP|Rb|Rf|Rp|U|b|bR|br|f|fP|fR|fp|fr|p|pF|pR|pf|pr|r|rB|rF|rP|rb|rf|rp|u))(?P<Quote>((?P<TripleQt>('''|\"\"\"))|(?P<SingleQt>(\"|'))))");
        let _ = compile(PSEUDO_TOKENS.as_str()); // should not panic
    }
}