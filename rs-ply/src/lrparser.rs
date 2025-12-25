use crate::data::StateMachine;
use crate::yacc_types::{YaccProduction, YaccSymbol};
use log::debug;
use pyo3::prelude::*;

/// The LR Parsing engine.  This is the core of the PLY parser generator.
#[pyclass]
#[derive(Debug)]
pub struct LRParser {
    pub fsm: Py<StateMachine>,
    pub errorf: Option<Py<PyAny>>,
    pub module: Py<PyAny>,
    pub errorok: bool,
    pub state: u16,
}

#[pymethods]
impl LRParser {
    #[new]
    #[pyo3(signature = (fsm, module, errorf=None))]
    fn new(fsm: Py<StateMachine>, module: Py<PyAny>, errorf: Option<Py<PyAny>>) -> Self {
        LRParser {
            fsm,
            errorf,
            module,
            errorok: true,
            state: 0,
        }
    }

    #[pyo3(signature = (input=None, lexer=None, debug=0, tracking=false))]
    fn parse<'py>(
        mut slf: PyRefMut<'py, Self>,
        py: Python<'py>,
        input: Option<&str>,
        lexer: Option<Bound<'py, PyAny>>,
        debug: u8,
        tracking: bool,
    ) -> PyResult<Py<PyAny>> {
        let lexer = lexer
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Lexer is required"))?;

        if let Some(inp) = input {
            lexer.call_method1("input", (inp,))?;
        }

        let mut statestack: Vec<u16> = vec![0];

        let start_sym = Py::new(
            py,
            YaccSymbol {
                r#type: "$end".to_string(),
                value: None,
                lineno: None,
                lexpos: None,
                endlineno: None,
                endlexpos: None,
            },
        )?;
        let mut symstack: Vec<Py<YaccSymbol>> = vec![start_sym];

        let mut lookahead: Option<Py<YaccSymbol>> = None;
        let mut lookaheadstack: Vec<Py<YaccSymbol>> = Vec::new();
        let mut errorcount: u8 = 0;
        let mut state: u16 = 0;
        slf.errorok = true;

        let module = slf.module.clone_ref(py);

        // Create YaccProduction once
        let pslice = Py::new(
            py,
            YaccProduction::new(lexer.clone().into(), module.clone_ref(py)),
        )?;

        loop {
            if debug > 0 {
                debug!("State  : {}", state);
            }

            // Get next action
            let mut action = {
                let fsm = slf.fsm.borrow(py);
                fsm.get_default_action(state).map(|a| a as i16)
            };

            if action.is_none() {
                if lookahead.is_none() {
                    if let Some(tok) = lookaheadstack.pop() {
                        lookahead = Some(tok);
                    } else {
                        let tok = lexer.call_method0("token")?;
                        if tok.is_none() {
                            let end_sym = Py::new(
                                py,
                                YaccSymbol {
                                    r#type: "$end".to_string(),
                                    value: None,
                                    lineno: None,
                                    lexpos: None,
                                    endlineno: None,
                                    endlexpos: None,
                                },
                            )?;
                            lookahead = Some(end_sym);
                        } else {
                            let r#type: String = tok.getattr("type")?.extract()?;
                            let value: Py<PyAny> = tok.getattr("value")?.extract()?;
                            let lineno: Option<usize> =
                                tok.getattr("lineno").ok().and_then(|a| a.extract().ok());
                            let lexpos: Option<usize> =
                                tok.getattr("lexpos").ok().and_then(|a| a.extract().ok());

                            let sym = Py::new(
                                py,
                                YaccSymbol {
                                    r#type,
                                    value: Some(value),
                                    lineno,
                                    lexpos,
                                    endlineno: lineno,
                                    endlexpos: lexpos.map(|l| l + 1),
                                },
                            )?;
                            lookahead = Some(sym);
                        }
                    }
                }

                let lh_type = {
                    let lh = lookahead.as_ref().unwrap().borrow(py);
                    lh.r#type.clone()
                };
                let fsm = slf.fsm.borrow(py);
                action = fsm.get_action(state as usize, &lh_type).map(|a| a as i16);
            }

            if let Some(act) = action {
                if act > 0 {
                    // SHIFT
                    statestack.push(act as u16);
                    state = act as u16;
                    symstack.push(lookahead.take().unwrap());
                    if errorcount > 0 {
                        errorcount -= 1;
                    }
                    continue;
                }

                if act < 0 {
                    // REDUCE
                    let (p_name, p_len, p_func) = {
                        let fsm = slf.fsm.borrow(py);
                        let p = fsm.expect_production((-act) as usize);
                        (p.name.clone(), p.len as usize, p.func.clone())
                    };

                    let mut sym_struct = YaccSymbol {
                        r#type: p_name.clone(),
                        value: None,
                        lineno: None,
                        lexpos: None,
                        endlineno: None,
                        endlexpos: None,
                    };

                    if p_len > 0 {
                        let stack_len = symstack.len();
                        let slice_start = stack_len - p_len;
                        let slice: Vec<Py<YaccSymbol>> = symstack[slice_start..]
                            .iter()
                            .map(|s| s.clone_ref(py))
                            .collect();

                        if tracking {
                            let t1_item = &slice[0];
                            let t1 = t1_item.borrow(py);
                            sym_struct.lineno = t1.lineno;
                            sym_struct.lexpos = t1.lexpos;
                            let tn_item = &slice[p_len - 1];
                            let tn = tn_item.borrow(py);
                            sym_struct.endlineno = tn.endlineno.or(tn.lineno);
                            sym_struct.endlexpos = tn.endlexpos.or(tn.lexpos);
                        }

                        let mut pslice_vec = Vec::with_capacity(p_len + 1);
                        // Manual copy of sym_struct because no Clone
                        let sym_copy = YaccSymbol {
                            r#type: sym_struct.r#type.clone(),
                            value: sym_struct.value.as_ref().map(|v| v.clone_ref(py)),
                            lineno: sym_struct.lineno,
                            lexpos: sym_struct.lexpos,
                            endlineno: sym_struct.endlineno,
                            endlexpos: sym_struct.endlexpos,
                        };
                        let sym_py = Py::new(py, sym_copy)?;
                        pslice_vec.push(sym_py.clone_ref(py));
                        pslice_vec.extend(slice);

                        {
                            let mut p_borrow = pslice.borrow_mut(py);
                            p_borrow.slice = pslice_vec;
                            p_borrow.stack = symstack.iter().map(|s| s.clone_ref(py)).collect();
                        }

                        if !p_func.is_empty() {
                            if let Ok(func) = slf.module.clone_ref(py).getattr(py, p_func.as_str())
                            {
                                func.call1(py, (pslice.clone_ref(py),))?;
                            }
                        }

                        for _ in 0..p_len {
                            symstack.pop();
                            statestack.pop();
                        }
                    } else {
                        // Empty production
                        if tracking {
                            sym_struct.lineno = lexer.getattr("lineno")?.extract()?;
                            sym_struct.lexpos = lexer.getattr("lexpos")?.extract()?;
                        }

                        let mut pslice_vec = Vec::with_capacity(1);
                        let sym_copy = YaccSymbol {
                            r#type: sym_struct.r#type.clone(),
                            value: sym_struct.value.as_ref().map(|v| v.clone_ref(py)),
                            lineno: sym_struct.lineno,
                            lexpos: sym_struct.lexpos,
                            endlineno: sym_struct.endlineno,
                            endlexpos: sym_struct.endlexpos,
                        };
                        let sym_py = Py::new(py, sym_copy)?;
                        pslice_vec.push(sym_py.clone_ref(py));

                        {
                            let mut p_borrow = pslice.borrow_mut(py);
                            p_borrow.slice = pslice_vec;
                            p_borrow.stack = symstack.iter().map(|s| s.clone_ref(py)).collect();
                        }

                        if !p_func.is_empty() {
                            if let Ok(func) = slf.module.clone_ref(py).getattr(py, p_func.as_str())
                            {
                                func.call1(py, (pslice.clone_ref(py),))?;
                            }
                        }
                    }

                    // Update sym with possibly new value from pslice[0]
                    let final_sym_py = pslice.borrow(py).slice[0].clone_ref(py);
                    symstack.push(final_sym_py);

                    let prev_state = *statestack.last().unwrap();
                    let fsm = slf.fsm.borrow(py);
                    let goto_state = fsm.expect_goto(prev_state as usize, &p_name)?;
                    statestack.push(goto_state);
                    state = goto_state;
                    continue;
                }

                if act == 0 {
                    // ACCEPT
                    let sym_py = symstack.last().unwrap();
                    let result = sym_py.borrow(py).value.as_ref().map(|v| v.clone_ref(py));
                    return Ok(result.unwrap_or_else(|| py.None()));
                }
            }

            return Err(pyo3::exceptions::PySyntaxError::new_err("Syntax error"));
        }
    }
}
