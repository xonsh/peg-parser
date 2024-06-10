def test_tokenize_str():
    from xonsh_tokenizer import tokenize_str

    tokens = tokenize_str("name = val")
    assert len(tokens) == 7
