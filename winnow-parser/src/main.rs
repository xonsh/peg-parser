use pyo3::prelude::*;
use pyo3::types::PyString;
use std::env;
use winnow_parser::parser::parse;
use winnow_parser::tokenizer::{tokenize, TokInfo, Token};

fn main() -> PyResult<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <code>", args[0]);
        return Ok(());
    }
    let code = &args[1];

    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        println!("Debugging code: {:?}", code);

        let source_py = PyString::new(py, code).into();
        let tokens = tokenize(py, source_py);
        let filtered_tokens: Vec<TokInfo> = tokens
            .into_iter()
            .filter(|t| {
                !matches!(
                    t.typ,
                    Token::WS | Token::NL | Token::COMMENT | Token::ENCODING | Token::TYPE_COMMENT
                )
            })
            .collect();

        println!(
            "Filtered tokens: {:?}",
            filtered_tokens
                .iter()
                .map(|t| (t.typ, t.span))
                .collect::<Vec<_>>()
        );

        match parse(py, code) {
            Ok(obj) => println!("Success: {:?}", obj),
            Err(e) => println!("Error: {:?}", e),
        }
        Ok(())
    })
}
