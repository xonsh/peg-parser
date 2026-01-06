use thiserror::Error;

/// Parser error.
#[derive(Debug, PartialEq, Clone, Error)]
pub enum Error {
    #[error("Incomplete")]
    Incomplete,
    #[error("Mismatch at {position}: {message}")]
    Mismatch { message: String, position: usize },
    #[error("Conversion failed at {position}: {message}")]
    Conversion { message: String, position: usize },
    #[error("{message} at {position}: {inner}")]
    Expect {
        message: String,
        position: usize,
        inner: Box<Error>,
    },
    #[error("{message} at {position}, (inner: {inner:?})")]
    Custom {
        message: String,
        position: usize,
        inner: Option<Box<Error>>,
    },
}

// impl error::Error for Error {
//     fn description(&self) -> &'static str {
//         "Parse error"
//     }
// }

/// Parser result, `Result<O>` ia alias of `Result<O, pom::Error>`.
pub type Result<O> = ::std::result::Result<O, Error>;
