def test_tokenize_str():
    from xonsh_tokenizer import tokenize_str

    source = "name = val"
    tokens = tokenize_str(source)
    assert [f"{t.type}: '{t.get_string(source)}'" for t in tokens] == [
        "NAME: 'name'",
        "WS: ' '",
        "OP: '='",
        "WS: ' '",
        "NAME: 'val'",
        "NEWLINE: ''",
        "ENDMARKER: ''",
    ]
