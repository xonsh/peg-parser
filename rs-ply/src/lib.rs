use pyo3::prelude::*;
use std::collections::HashMap;
use std::io::BufRead;

#[pyclass(get_all, frozen)]
#[derive(Debug, Clone)]
struct Production {
    name: String,
    str: String,
    func: String,
    len: u8,
}

type MiniProduction = (String, u8, String, Option<String>);

/// the int keys and values are very small around -2k to +2k
type Actions = HashMap<String, i16>;
type Goto = HashMap<String, u16>;

/// A class for representing parser objects.
#[pyclass]
struct StateMachine {
    /// A field for the name
    productions: Vec<Production>,
    actions: Vec<Actions>,
    gotos: Vec<Goto>,

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

#[pymethods]
impl StateMachine {
    #[new]
    fn new_from_file(file_path: &str) -> PyResult<Self> {
        // deserialize from JSONL file
        let file = std::fs::File::open(file_path)?;
        let mut reader = std::io::BufReader::new(file).lines();

        let first_line = reader.next().unwrap()?;
        let _prods: Vec<MiniProduction> = serde_json::from_str(&first_line).unwrap();
        let second_line = reader.next().unwrap()?;
        let actions: Vec<Actions> = serde_json::from_str(&second_line).unwrap();
        let third_line = reader.next().unwrap()?;
        let gotos: Vec<Goto> = serde_json::from_str(&third_line).unwrap();
        let mut productions = vec![];
        let mut defaults: HashMap<u16, i16> = HashMap::new();

        for (state, act) in actions.iter().enumerate() {
            if act.len() == 1 {
                // insert first value of act to defaults
                defaults.insert(state as u16, act.values().next().unwrap().clone());
            }
        }

        for (name, len, text, func) in _prods {
            let prod = Production {
                name,
                str: text,
                func: func.unwrap_or("".to_string()),
                len,
            };
            productions.push(prod);
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

    fn get_action(&self, state: u16, sym: &str) -> Option<i16> {
        let symbols = self.actions.get(state as usize)?;
        symbols.get(sym).copied()
    }
    fn get_production(&self, index: usize) -> Production {
        let prod = self.productions.get(index).unwrap();
        prod.clone()
    }
    fn get_goto(&self, index: usize, sym: &str) -> Option<u16> {
        self.gotos.get(index)?.get(sym).copied()
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
