mod token;
mod tok_info;

use pyo3::prelude::*;

pub use token::Token;
pub use tok_info::TokInfo;

/// A Python module implemented in Rust.
#[pymodule]
mod xtokens {
    use pyo3::prelude::*;

    #[pymodule_export]
    use crate::token::Token;

    #[pymodule_export]
    use crate::tok_info::TokInfo;
}
