mod tokenizer;
mod montyc_tok;

use rustpython_parser::parser::parse_expression;

fn main() {
    let python_source = "print('Hello world')";
    let python_ast = parse_expression(python_source, "<code>").unwrap();
    println!("{:#?}", python_ast);
    // read a line input
    let mut input = String::new();
    println!("Enter a number: ");
    // wait untile we check memory usage
    std::io::stdin().read_line(&mut input).unwrap();
}

// write a test that parser
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_parser() {
        use sysinfo::{System, SystemExt, get_current_pid, ProcessExt};
        let pid = get_current_pid().unwrap();
        let sys = System::new_all();
        let proc = sys.process(pid).unwrap();
        let python_source = "print('Hello world')";
        let python_ast = parse_expression(python_source, "<code>").unwrap();
        println!("{}", proc.memory());
    }
}