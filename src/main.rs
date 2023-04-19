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
