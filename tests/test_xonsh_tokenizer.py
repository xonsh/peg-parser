def test_tokenize_str():
    from xonsh_tokenizer import tokenize_str

    tokens = tokenize_str("name = val")
    assert [f"{t.type}: '{t.string}'" for t in tokens] == [
        "NAME: 'name'",
        "WS: ' '",
        "OP: '='",
        "WS: ' '",
        "NAME: 'val'",
        "NEWLINE: ''",
        "ENDMARKER: ''",
    ]
