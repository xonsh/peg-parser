# xonsh-parser

<p align="center">
    <em>Xonsh parser using PLY</em>
</p>

[![build](https://github.com/jnoortheen/xonsh-parser/workflows/Build/badge.svg)](https://github.com/jnoortheen/xonsh-parser/actions)
[![codecov](https://codecov.io/gh/jnoortheen/xonsh-parser/branch/master/graph/badge.svg)](https://codecov.io/gh/jnoortheen/xonsh-parser)
[![PyPI version](https://badge.fury.io/py/xonsh-parser.svg)](https://badge.fury.io/py/xonsh-parser)

---

**Documentation**: <a href="https://jnoortheen.github.io/xonsh-parser/" target="_blank">https://jnoortheen.github.io/xonsh-parser/</a>

**Source Code**: <a href="https://github.com/jnoortheen/xonsh-parser" target="_blank">https://github.com/jnoortheen/xonsh-parser</a>

---

## Development

### Setup environment

We use [Hatch](https://hatch.pypa.io/latest/install/) to manage the development environment and production build. Ensure it's installed on your system.

### Run unit tests

You can run all the tests with:

```bash
task test

# to watch for changes and run tests
task test --watch -- -x --ff
```

### Format the code

Execute the following command to apply linting and check typing:

```bash
hatch run lint
```

### Publish a new version

You can bump the version, create a commit and associated tag with one command:

```bash
hatch version patch
```

```bash
hatch version minor
```

```bash
hatch version major
```

Your default Git text editor will open so you can add information about the release.

When you push the tag on GitHub, the workflow will automatically publish it on PyPi and a GitHub release will be created as draft.

## Serve the documentation

You can serve the Mkdocs documentation with:

```bash
hatch run docs-serve
```

It'll automatically watch for changes in your code.

## License

This project is licensed under the terms of the MIT license.

## Credits

- Thanks to [pegen](https://github.com/we-like-parsers/pegen) project for the Python version of the `CPython's` PEG parser
- Thanks to [intellij-pegen-plugin](https://github.com/vpoverennov/pegen-plugin)
