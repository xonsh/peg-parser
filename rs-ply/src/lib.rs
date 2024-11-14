use std::collections::HashMap;
use std::io::BufRead;
use pyo3::prelude::*;

#[derive(Debug)]
struct Production {
    name: String,
    text: String,
    func: String,
    len: u8,
}

type MiniProduction = (String, u8, String, Option<String>);
type Action = HashMap<String, i16>;
type Goto = HashMap<String, u16>;

/// A class for representing parser objects.
#[pyclass]
struct StateMachine {
    /// A field for the name
    productions: Vec<Production>,
    actions: Vec<Action>,
    gotos: Vec<Goto>,
}

#[pymethods]
impl StateMachine {
    // fn empty() -> Self {
    //     Self {
    //         productions: Vec::new(),
    //         actions: Vec::new(),
    //         gotos: Vec::new(),
    //     }
    // }

    #[new]
    fn new_from_file(file_path: &str) -> PyResult<Self> {
        // deserialize from JSONL file
        let file = std::fs::File::open(file_path)?;
        let mut reader = std::io::BufReader::new(file).lines();

        let first_line = reader.next().unwrap()?;
        let _prods: Vec<MiniProduction> = serde_json::from_str(&first_line).unwrap();
        let second_line = reader.next().unwrap()?;
        let actions: Vec<Action> = serde_json::from_str(&second_line).unwrap();
        let third_line = reader.next().unwrap()?;
        let gotos: Vec<Goto> = serde_json::from_str(&third_line).unwrap();
        let mut productions = vec![];

        for (name, len, text, func) in _prods {
            let prod = Production {
                name,
                text,
                func: func.unwrap_or("".to_string()),
                len,
            };
            productions.push(prod);
        }

        Ok(Self {
            productions,
            actions,
            gotos,
        })
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn rs_ply(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<StateMachine>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse() {
        let path = "/Users/noor/src/py/xonsh-parser/ply_parser/parsers/v310.Parser.table.v1.jsonl";
        let sm = StateMachine::new_from_file(path).unwrap();
        println!("{:?}", sm.productions.len());
    }
}