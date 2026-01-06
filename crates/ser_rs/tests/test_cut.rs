use ser_rs::parser::*;
use ser_rs::result::Error;

#[test]
fn test_cut_parser() {
    // Parser: sym(b'a') + sym(b'b').cut() | sym(b'c')
    // Logic:
    // 1. input "ab" -> matches 'a', 'b', success.
    // 2. input "c" -> matches 'c' (first part fails mismatch 'a', backtracking works).
    // 3. input "az" -> matches 'a', 'b' fails. .cut() converts this to Cut/Expect. Choice | sees this and aborts. 'c' is NOT tried.

    // We map to () to unify return types for the choice
    let p = (sym(b'a') + sym(b'b').cut()).map(|_| ()) | sym(b'c').map(|_| ());

    // Case 1: Success "ab"
    assert!(p.parse(b"ab").is_ok());

    // Case 2: Success "c" (backtracking works if failure before cut)
    assert!(p.parse(b"c").is_ok());

    // Case 3: Failure "az" (cut prevents backtracking)
    let res = p.parse(b"az");
    match res {
        Err(Error::Cut { .. }) => assert!(true),
        // Depending on implementation details, it might be Expect or Cut.
        // My implementation wraps mismatch in Cut.
        Err(e) => panic!("Expected Cut error, got {:?}", e),
        Ok(_) => panic!("Should fail"),
    }
}
