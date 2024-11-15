use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use serde::Deserialize;
use std::collections::HashMap;
use std::io::BufRead;

#[pyclass(get_all, frozen)]
#[derive(Debug, Clone, Deserialize)]
struct Production {
    name: String,
    str: String,
    func: String,
    len: u8,
}

type MiniProduction = (String, u8, String, Option<String>);

/// the int keys and values are very small around -2k to +2k
type Actions = HashMap<String, i16>;
type Gotos = HashMap<String, u16>;

/// A class for representing parser objects.
#[pyclass]
#[derive(Debug)]
pub struct StateMachine {
    /// A field for the name
    productions: Vec<Production>,
    actions: Vec<Actions>,
    gotos: Vec<Gotos>,

    /// # Defaulted state support.
    //     # This method identifies parser states where there is only one possible reduction action.
    //     # For such states, the parser can make a choose to make a rule reduction without consuming
    //     # the next look-ahead token.  This delayed invocation of the tokenizer can be useful in
    //     # certain kinds of advanced parsing situations where the lexer and parser interact with
    //     # each other or change states (i.e., manipulation of scope, lexer states, etc.).
    //     #
    //     # See:  http://www.gnu.org/software/bison/manual/html_node/Default-Reductions.html#Default-Reductions
    defaults: HashMap<u16, i16>,
}

fn json_error_to_py_err(err: serde_json::Error) -> PyErr {
    PyValueError::new_err(err.to_string())
}

fn parse_json<'a, T>(input: &'a str) -> Result<T, PyErr>
where
    T: serde::de::Deserialize<'a>,
{
    serde_json::from_str(input).map_err(json_error_to_py_err)
}

#[pymethods]
impl StateMachine {
    #[new]
    fn new_from_file(file_path: &str) -> PyResult<Self> {
        // deserialize from JSONL file
        let file = std::fs::File::open(file_path)?;
        let mut reader = std::io::BufReader::new(file).lines();

        let first_line = reader.next().unwrap()?;
        let productions = parse_json::<Vec<MiniProduction>>(&first_line)?
            .iter()
            .map(|(name, len, text, func)| Production {
                name: name.to_string(),
                str: text.to_string(),
                func: func.clone().unwrap_or("".to_string()),
                len: len.clone(),
            })
            .collect();
        let second_line = reader.next().unwrap()?;
        let actions: Vec<Actions> = parse_json(&second_line)?;
        let third_line = reader.next().unwrap()?;
        let gotos: Vec<Gotos> = parse_json(&third_line)?;
        let mut defaults: HashMap<u16, i16> = HashMap::new();

        for (state, act) in actions.iter().enumerate() {
            if act.len() == 1 {
                let first = act.values().next().unwrap().clone();
                if first < 0 {
                    // insert first value of act to defaults
                    defaults.insert(state as u16, act.values().next().unwrap().clone());
                }
            }
        }

        Ok(Self {
            productions,
            actions,
            gotos,
            defaults,
        })
    }

    fn get_default_action(&self, state: u16) -> Option<i16> {
        self.defaults.get(&state).copied()
    }

    fn get_action(&self, state: usize, sym: &str) -> Option<i16> {
        let symbols = self.actions.get(state).unwrap();
        let action = symbols.get(sym);
        action.map(|x| *x)
    }
    fn expect_production(&self, index: usize) -> Production {
        let prod = self.productions.get(index).unwrap();
        prod.clone()
    }
    fn expect_goto(&self, state: usize, sym: &str) -> PyResult<u16> {
        let gotos = self
            .gotos
            .get(state)
            .ok_or_else(|| PyIndexError::new_err(format!("Goto state {} not found", state)))?;
        let got = gotos.get(sym).ok_or_else(|| {
            PyIndexError::new_err(format!("Goto symbol {}.{} not found", state, sym))
        })?;
        Ok(*got)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse() {
        let path = "/Users/noor/src/py/xonsh-parser/ply_parser/parsers/v310.Parser.table.v1.jsonl";
        pyo3::prepare_freethreaded_python();
        let sm = StateMachine::new_from_file(path);
        if sm.is_ok() {
            let sm = sm.unwrap();
            println!("{:?} {:?}", sm.productions.len(), sm.actions.len());
        } else {
            println!("Failed to create {:?}", sm)
        }
    }
}
