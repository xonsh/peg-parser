a = 10
f"{a * x()}"


"no formatted values"
f"eggs {a * x()} spam {b + y()}"


a = 10
f"{a * x()} {a * x()} {a * x()}"


a = 10
f"""
  {a
     *
       x()}
non-important content
"""


a = f"""
          {blech}
    """


x = f" {test(t)}"


x = (
    "wat",
    "wat",
    b"wat",
    b"wat",
    "wat",
    "wat",
)
y = (
    """wat""",
    """wat""",
    b"""wat""",
    b"""wat""",
    """wat""",
    """wat""",
)
# x = (
#         'PERL_MM_OPT', (
#             f'wat'
#             f'some_string={f(x)} '
#             f'wat'
#         ),
# )


f"{expr:}"


foo = 3.14159
verbosePrint(f"Foo {foo:.3} bar.")


st = "string"
f"{st!r}"
