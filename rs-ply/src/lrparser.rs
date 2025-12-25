use crate::data::StateMachine;
use crate::yacc_types::YaccSymbol;
use log::{debug, info};
use pyo3::prelude::*;
use pyo3::PyObject;

struct ParserState {
    statestack: Vec<u16>,
    symstack: Vec<YaccSymbol>,
    lookahead: Option<YaccSymbol>,
    lookaheadstack: Vec<YaccSymbol>,
    errorcount: u8,
    state: u16,
    errtoken: Option<YaccSymbol>,
    tracking: bool,
}

impl ParserState {
    fn log_state(&self) {
        debug!("State  : {}", self.state);
    }

    fn log_stack(&self) {
        debug!("Stack  : {:?} . {:?}", self.symstack, self.lookahead);
    }
}

/// The LR Parsing engine.  This is the core of the PLY parser generator.
#[pyclass]
#[derive(Debug)]
pub struct LRParser {
    fsm: StateMachine,
    errorf: Option<PyObject>,
    module: PyObject,
    errorok: bool,
}

#[pymethods]
impl LRParser {
    #[new]
    fn new(path: &str, module: PyObject, errorf: Option<PyObject>) -> PyResult<Self> {
        let fsm = StateMachine::new_from_file(path)?;
        let slf = LRParser {
            fsm,
            errorf,
            module,
            errorok: true,
        };
        Ok(slf)
    }

    fn parse<'py>(
        slf: &Bound<'py, Self>,
        _py: Python<'py>,
        input: &str,
        lexer: PyObject,
        debug: bool,
        tracking: bool,
    ) -> PyResult<PyObject> {
        if debug {
            info!("PLY: PARSE DEBUG START");
        }
        let _parser_state = slf
            .borrow()
            ._initialize_parser_state(lexer, input, tracking);
        // Production object passed to grammar rules
        // let pslice = YaccProduction::new(py, lexer.bind(py), slf, parser_state.symstack);

        // while let Some(action) = self._get_next_action(&parser_state) {
        //     if debug {
        //         parser_state.log_state();
        //     }
        //     if action > 0 {
        //         self._handle_shift(&parser_state, action);
        //         continue;
        //     } else if action < 0 {
        //         // reduce a symbol on the stack, emit a production
        //         // let a = self._handle
        //         todo!();
        //     }
        // }
        todo!()
    }
    fn _initialize_parser_state(&self, _lexer: PyObject, _input: &str, _tracking: bool) -> () {
        todo!()
    }
}
