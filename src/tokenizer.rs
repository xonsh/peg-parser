use logos::Logos;

// todo: add string interning


// https://github.com/python/cpython/blob/main/Grammar/Tokens
#[derive(Debug, Logos, PartialEq, Clone)]
pub enum Token {

    // -- Token literals
    #[token("(")]LPAR,
    #[token(")")]RPAR,
    #[token("[")]LSQB,
    #[token("]")]RSQB,
    #[token(":")]COLON,
    #[token(",")]COMMA,
    #[token(";")]SEMI,
    #[token("+")]PLUS,
    #[token("-")]MINUS,
    #[token("*")]STAR,
    #[token("/")]SLASH,
    #[token("|")]VBAR,
    #[token("&")]AMPER,
    #[token("<")]LESS,
    #[token(">")]GREATER,
    #[token("=")]EQUAL,
    #[token(".")]DOT,
    #[token("%")]PERCENT,
    #[token("{")]LBRACE,
    #[token("}")]RBRACE,
    #[token("==")]EQEQUAL,
    #[token("!=")]NOTEQUAL,
    #[token("<=")]LESSEQUAL,
    #[token(">=")]GREATEREQUAL,
    #[token("~")]TILDE,
    #[token("^")]CIRCUMFLEX,
    #[token("<<")]LEFTSHIFT,
    #[token(">>")]RIGHTSHIFT,
    #[token("**")]DOUBLESTAR,
    #[token("+=")]PLUSEQUAL,
    #[token("-=")]MINEQUAL,
    #[token("*=")]STAREQUAL,
    #[token("/=")]SLASHEQUAL,
    #[token("%=")]PERCENTEQUAL,
    #[token("&=")]AMPEREQUAL,
    #[token("|=")]VBAREQUAL,
    #[token("^=")]CIRCUMFLEXEQUAL,
    #[token("<<=")]LEFTSHIFTEQUAL,
    #[token(">>=")]RIGHTSHIFTEQUAL,
    #[token("**=")]DOUBLESTAREQUAL,
    #[token("//")]DOUBLESLASH,
    #[token("//=")]DOUBLESLASHEQUAL,
    #[token("@")]AT,
    #[token("@=")]ATEQUAL,
    #[token("->")]RARROW,
    #[token("...")]ELLIPSIS,
    #[token(":=")]COLONEQUAL,
    #[token("!")]EXCLAMATION,

    // special tokens
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
    TYPE_IGNORE,
    TYPE_COMMENT,
    SOFT_KEYWORD,
    FSTRING_START,
    FSTRING_MIDDLE,
    FSTRING_END,
    ERRORTOKEN,
    COMMENT,
    NL,
    ENCODING,

    // keywords
    #[token("True")]
    True,

    #[token("False")]
    False,

    #[token("None")]
    None,

    #[token("is")]
    Is,

    #[token("or")]
    Or,

    #[token("not")]
    Not,

    #[token("await")]
    Await,

    #[token("async")]
    Async,

    #[token("if")]
    If,

    #[token("elif")]
    Elif,

    #[token("else")]
    Else,

    #[token("class")]
    ClassDef,

    #[token("def")]
    FnDef,

    #[token("return")]
    Return,

    #[token("while")]
    While,

    #[token("pass")]
    Pass,

    #[token("continue")]
    Continue,

    #[token("in")]
    In,

    #[token("break")]
    Break,

    #[token("from")]
    From,

    #[token("import")]
    Import,

    #[token("raise")]
    Raise,

    #[token("assert")]
    Assert,

    #[token("del")]
    Del,

    #[token("global")]
    Global,

    #[token("yield")]
    Yield,

    #[token("nonlocal")]
    Nonlocal,

    #[token(r"\")]
    Escape,

    #[token("\n")]
    Newline,

    #[token("\u{c}")]
    FormFeed,

    // -- Regex rules
    #[regex(r"\t| ")]
    Whitespace,

    #[regex(r"-?\d+")]
    #[regex(r"-?0[xX][0-9a-fA-F]+")]
    Number,

    #[regex(r"#[^\n]*")]
    Comment,

    // -- String regex's (thank god I managed to nerdsnipe Quirl to do this for me.)
    #[regex(r#"([rR]|[fF]|u|[rR][fF]|[fF][rR])?'((\\.)|[^'\\\r\n])*'"#)]
    #[regex(r#"([rR]|[fF]|u|[rR][fF]|[fF][rR])?'''((\\.)|[^\\']|'((\\.)|[^\\'])|''((\\.)|[^\\']))*'''"#)]
    #[regex(r#"([rR]|[fF]|u|[rR][fF]|[fF][rR])?"((\\.)|[^"\\\r\n])*""#)]
    #[regex(r#"([rR]|[fF]|u|[rR][fF]|[fF][rR])?"""((\\.)|[^\\"]|"((\\.)|[^\\"])|""((\\.)|[^\\"]))*""""#)]
    StringLiteral,

    #[regex(r#"([bB]|[rR][bB]|[bB][rR])'((\\\p{ASCII})|[\p{ASCII}&&[^'\\\r\n]])*'"#)]
    #[regex(r#"([bB]|[rR][bB]|[bB][rR])'''((\\\p{ASCII})|[\p{ASCII}&&[^\\']]|'((\\\p{ASCII})|[\p{ASCII}&&[^\\']])|''((\\\p{ASCII})|[\p{ASCII}&&[^\\']]))*'''"#)]
    ByteLiteral,

    // -- SpanRef tokens
    #[regex("[a-zA-Z_][_a-zA-Z0-9]*")]
    RawIdent,
}

fn tokenize(source: &str) -> Vec<Token> {
    Token::lexer(source).map(|x| x.unwrap()).collect::<Vec<_>>()
}

// test the tokenizer
#[test]
fn test_tokens() {
    let tokens = tokenize("a = b");
    println!("{:?}", tokens);
    // assert_eq!(lexer.next().unwrap().unwrap(), Token::RawIdent);
    // assert_eq!(lexer.next().unwrap().unwrap(), PyToken::Period);
    // assert_eq!(lexer.next().unwrap().unwrap(), PyToken::Text);
}
