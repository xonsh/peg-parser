use crate::tokenizer::tok::TokInfo;

pub(crate) enum LoopAction {
    Break,
    None,
}

pub(crate) type LoopResult = (LoopAction, Vec<TokInfo>);
