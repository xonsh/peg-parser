# CHANGELOG



## v0.3.0 (2024-06-07)

### Chore

* chore: add release command ([`89e8758`](https://github.com/jnoortheen/xonsh-parser/commit/89e8758cc9122152c9aae19b54db48f300fff228))

### Feature

* feat: optimize calling self._mark() ([`002d853`](https://github.com/jnoortheen/xonsh-parser/commit/002d853f897f9df2525eb5c4bd815943f43ba6e8))

* feat: include generated parser in the repo ([`e87ed02`](https://github.com/jnoortheen/xonsh-parser/commit/e87ed020b3b44dd0f537733100bb67b686e3ee06))

### Test

* test: update test fixture ([`6999da8`](https://github.com/jnoortheen/xonsh-parser/commit/6999da80acf2009920aea363bc96721fdb68f4ae))


## v0.2.0 (2024-06-03)

### Chore

* chore: add task to compile meta parser

and add more benchmarks ([`263f7f4`](https://github.com/jnoortheen/xonsh-parser/commit/263f7f4504530add848f5a875b493f6d2e91cc29))

### Documentation

* docs: baseline memory usage and parser file size ([`57b9f92`](https://github.com/jnoortheen/xonsh-parser/commit/57b9f92f39814a86ed7bc146856c7f94a33fd11a))

### Feature

* feat: optimize gathered rule generation ([`6b38b59`](https://github.com/jnoortheen/xonsh-parser/commit/6b38b590f5154ab16482ab07d1375cceb4ab28fb))

* feat: handle elem* and elem+ repetition

without code duplication to reduce the generated parser size ([`0bd67ca`](https://github.com/jnoortheen/xonsh-parser/commit/0bd67cab472ed4f4d948e9a4073e7af973865344))

* feat: optimize getting locations

chore: merge frequently run profile suits ([`18b6be1`](https://github.com/jnoortheen/xonsh-parser/commit/18b6be193034b7e625566807d34ec0f0c336c64d))

* feat: tersely pack return statement generated ([`afbcd9d`](https://github.com/jnoortheen/xonsh-parser/commit/afbcd9df437925bb403c4650550543280604d77c))

* feat: no more empty spaces in the generated parser actions ([`15d974c`](https://github.com/jnoortheen/xonsh-parser/commit/15d974cfe2fcb9d55bff8e30bb5ce3d24d6adc81))

### Fix

* fix: test errors for the change in ensure_real function ([`fa37942`](https://github.com/jnoortheen/xonsh-parser/commit/fa379429f793de6eb9f9f9ad958ed56c431980e7))

### Refactor

* refactor: short start_location names in generated parser ([`4c011b2`](https://github.com/jnoortheen/xonsh-parser/commit/4c011b2a181c630d3ff6ac7e5f6eb5afd9b625f7))

* refactor: extract xonsh specific parser generation

to a separate module ([`e996217`](https://github.com/jnoortheen/xonsh-parser/commit/e996217d6a4ddd6c62143c017c743216cb1ec756))

* refactor: remove unused files from pegen project ([`cd1a65a`](https://github.com/jnoortheen/xonsh-parser/commit/cd1a65a58e11c4e64979a4e8e787ace6efcb03da))

* refactor: optimize memoize_left_rec ([`3622d2e`](https://github.com/jnoortheen/xonsh-parser/commit/3622d2eff399ce65c1909b2ffc78ec9661806409))

* refactor: optimize memoize function

separate verbose mode operations ([`a14dba2`](https://github.com/jnoortheen/xonsh-parser/commit/a14dba23fa1763b645fe93a4a3d801d908fe3434))

### Test

* test: fix building parser fixture ([`9ead0e4`](https://github.com/jnoortheen/xonsh-parser/commit/9ead0e4ebede640495fab525eecd9b1566fb21d8))

* test: remove memsuit as it is not relevant ([`8378811`](https://github.com/jnoortheen/xonsh-parser/commit/837881110ca8a476e3a1869992713b80118ad12c))

* test: add large file benchmarking ([`d47e6d7`](https://github.com/jnoortheen/xonsh-parser/commit/d47e6d73758c9c25a7fa9054c7f82b209708ccd3))


## v0.1.0 (2024-05-30)

### Breaking

* refactor!: make walrus operator default in tokenizer ([`8644077`](https://github.com/jnoortheen/xonsh-parser/commit/86440770527bbb65efa063b98fcc58fcd56aa4ca))

* fix!: make tokenizer py3.9+

any minor version will likely break ([`5953b68`](https://github.com/jnoortheen/xonsh-parser/commit/5953b68a4c15f3fb4fbf9d7022f40292c04bd0ef))

* refactor!: make async/await keywords

now the xonsh tokenizer is py3.7+ and py3.6 support is dropped ([`9912fe3`](https://github.com/jnoortheen/xonsh-parser/commit/9912fe3e6611066d31b11b2b0d3b653c2362e41a))

### Chore

* chore: update profiling code ([`1ce7736`](https://github.com/jnoortheen/xonsh-parser/commit/1ce7736b3c3b8ea8b83d3cb98155a14100d54049))

* chore: update benchmark suit ([`4a6c0da`](https://github.com/jnoortheen/xonsh-parser/commit/4a6c0da566034dcea9ca2a6b39ec84182984f8b8))

* chore: update ci tests ([`b5ddd3b`](https://github.com/jnoortheen/xonsh-parser/commit/b5ddd3bc6d8e02244e274c314be8e791dee25b1a))

* chore: cleanup repo ([`1cc3339`](https://github.com/jnoortheen/xonsh-parser/commit/1cc3339d9cd53c0bf492460bfe83f63b761d6942))

* chore: fix ci test ([`adcd2a8`](https://github.com/jnoortheen/xonsh-parser/commit/adcd2a887880d65c2ce4f44cc6d73ac8b5196863))

* chore: exit at first fail ([`273254d`](https://github.com/jnoortheen/xonsh-parser/commit/273254de29b23a42dcdaf71d364060d82f57886b))

* chore: set timeout ([`4e02683`](https://github.com/jnoortheen/xonsh-parser/commit/4e026831f48461c7c95856946cd5b0813425a047))

* chore: use latest pip in CI ([`de33bd4`](https://github.com/jnoortheen/xonsh-parser/commit/de33bd46f27e3d46e79016429f86cef58e718e92))

* chore: setup github actions ([`202ac4f`](https://github.com/jnoortheen/xonsh-parser/commit/202ac4fed12f33a7710274bf628ec49e301f8a5f))

* chore: update tasks ([`25550f8`](https://github.com/jnoortheen/xonsh-parser/commit/25550f8dfda92e25944289a0a695f25263b3ad64))

* chore: add pytest-testmondata ([`d16a1b1`](https://github.com/jnoortheen/xonsh-parser/commit/d16a1b1d36e2a4ed4d4ad936b318caf508b1d86b))

* chore: add task to test ([`91ff36b`](https://github.com/jnoortheen/xonsh-parser/commit/91ff36b68965b5d7c098454709b3b11c430e1956))

* chore: update tests ([`ecddd55`](https://github.com/jnoortheen/xonsh-parser/commit/ecddd55faffabfd23593a6df76b7ee383fa9ddb5))

* chore: use single xonsh.gram ([`d8decfd`](https://github.com/jnoortheen/xonsh-parser/commit/d8decfd037ac6bfc172aad8af459a617f3695b3d))

* chore: add ipython ([`c1aa19e`](https://github.com/jnoortheen/xonsh-parser/commit/c1aa19e0ae56cb5d9aac7200f079d3d59cf47778))

* chore: update tasks ([`cb6d0a1`](https://github.com/jnoortheen/xonsh-parser/commit/cb6d0a10d2c22a818c37ca497d9c28f058247f76))

* chore: add flask deps for pegen-web module ([`88bcc1a`](https://github.com/jnoortheen/xonsh-parser/commit/88bcc1ab7b62c7e22cf092192fca1317b249f16e))

* chore: update mypy config ([`ce9ade6`](https://github.com/jnoortheen/xonsh-parser/commit/ce9ade68beae156727df8c0d3e43b2e7eea62a12))

* chore: remove taskfiles ([`cf45fb7`](https://github.com/jnoortheen/xonsh-parser/commit/cf45fb7d96ad826a05bed75323f1d7570fcc7716))

* chore: update ruff settings ([`3b68f45`](https://github.com/jnoortheen/xonsh-parser/commit/3b68f45f876f45f4b4f1d8a11fa986df6a1d3226))

* chore: upgrade pre-commit plugins ([`d66b247`](https://github.com/jnoortheen/xonsh-parser/commit/d66b247dcb7b5f53d5b073e267ece4ea0e1b4f85))

* chore: update taskfile ([`e3a9c41`](https://github.com/jnoortheen/xonsh-parser/commit/e3a9c4172c85d3fb4ea66ca571b06464d58e275c))

* chore: update ignore ([`f579b17`](https://github.com/jnoortheen/xonsh-parser/commit/f579b176f1cc8534d49304c193333133043135b5))

* chore: upgrade pre-commit plugins ([`daafc93`](https://github.com/jnoortheen/xonsh-parser/commit/daafc930873ebee07d352a8b944dcb16de1027c2))

* chore: test mem usage ([`9e09af3`](https://github.com/jnoortheen/xonsh-parser/commit/9e09af3e71dc8b5f7a814255a3b58cff986db0f1))

* chore: black format ply other than yacc.py ([`a589ea8`](https://github.com/jnoortheen/xonsh-parser/commit/a589ea8edf28ac797ff6bc4a396b2f3624e827dc))

* chore: consider rust bindings ([`e45d3cd`](https://github.com/jnoortheen/xonsh-parser/commit/e45d3cd500e83b1b215db153bc6314ef4f28f0f4))

* chore: add monkeytype commands ([`8cb16ae`](https://github.com/jnoortheen/xonsh-parser/commit/8cb16ae1318991f2b970330a5c26af670ea46a95))

* chore: use monkeytype annotate code ([`5ee23c6`](https://github.com/jnoortheen/xonsh-parser/commit/5ee23c639177f74e0d33257e640558acc5bf1f9a))

* chore: add pre-commit ([`f8a2ddd`](https://github.com/jnoortheen/xonsh-parser/commit/f8a2ddd89b41ac03cb337db5f727b5029151deef))

* chore: use asv for benchmarks ([`e7e9eb7`](https://github.com/jnoortheen/xonsh-parser/commit/e7e9eb7bf085123946061500efcd4f0fb5ee50ea))

* chore: use pdm for installing deps ([`27b1095`](https://github.com/jnoortheen/xonsh-parser/commit/27b109523da6086ecf51ab80dedb0d9e21b17365))

* chore: add tasks ([`63845c8`](https://github.com/jnoortheen/xonsh-parser/commit/63845c88446f4bfcd8231f71dc258ff751f0a1b9))

* chore: ignore IDE ([`c167e8f`](https://github.com/jnoortheen/xonsh-parser/commit/c167e8fbe3e39ffb3cc195b0269e95422c05b3f6))

* chore: initial commit generated from cookiecutter

https://github.com/frankie567/cookiecutter-hipster-pypackage ([`d6d80c5`](https://github.com/jnoortheen/xonsh-parser/commit/d6d80c578584322d92388b3aa2121a70f11d7780))

### Documentation

* docs: add profile results ([`7223a9d`](https://github.com/jnoortheen/xonsh-parser/commit/7223a9dd63ebc53669c408d2ea80cf1044fa8646))

* docs: due credits ([`467ebc4`](https://github.com/jnoortheen/xonsh-parser/commit/467ebc4c2dafb20c9d355e14c3b51fb2e58bdb35))

* docs: update todos ([`f1385e8`](https://github.com/jnoortheen/xonsh-parser/commit/f1385e80ce9fdf6189cb028bdd0eb58af69a9776))

* docs: mark pegen checking done ([`c025bff`](https://github.com/jnoortheen/xonsh-parser/commit/c025bfff991f8d1be0ee542f7e794cd6fb0ca67c))

* docs: add todo items ([`6490437`](https://github.com/jnoortheen/xonsh-parser/commit/649043746fc457feed6d0eeee8190bfc9b40e1c0))

* docs: update todos ([`4ee5659`](https://github.com/jnoortheen/xonsh-parser/commit/4ee56590040458feeb39a2d264a5ae3791f8360e))

* docs: add todo ([`6fa67ec`](https://github.com/jnoortheen/xonsh-parser/commit/6fa67ec74ff09155e77f6ec996e95ba431ee478f))

* docs: add benchmark results ([`3c1ee8b`](https://github.com/jnoortheen/xonsh-parser/commit/3c1ee8b30b5716dac5ab6e42b1ea0df11a6f439b))

* docs: benchmark results ([`b1d5b1e`](https://github.com/jnoortheen/xonsh-parser/commit/b1d5b1e63876298aa3d95f1e90de5c1271d86473))

### Feature

* feat: compile with mypyc optionally ([`e4dd77a`](https://github.com/jnoortheen/xonsh-parser/commit/e4dd77acf9707c711fe8bb13d666a21006788ad6))

* feat: strict mypy checking ([`caba69c`](https://github.com/jnoortheen/xonsh-parser/commit/caba69c810be6fd8bd7f1bb58069542c217d8461))

* feat: parse f-strings py312 ([`da9369f`](https://github.com/jnoortheen/xonsh-parser/commit/da9369f27eaa0ac5c90e2a43d7901671493ae0cf))

* feat: tokenize py312 fstrings

https://peps.python.org/pep-0701/ ([`5955aa5`](https://github.com/jnoortheen/xonsh-parser/commit/5955aa5e80257889fbef6b8a2ea987b717d9e2b5))

* feat: use enums for Tokens

and parse exact-tokens as OP ([`d7a146b`](https://github.com/jnoortheen/xonsh-parser/commit/d7a146b8607456c00252be835b4d64e551d36af4))

* feat: generate parser during build ([`021c6fe`](https://github.com/jnoortheen/xonsh-parser/commit/021c6fe7aa1fb815176523bb3efab7277124f209))

* feat: implement with macro multi indents ([`43a0f20`](https://github.com/jnoortheen/xonsh-parser/commit/43a0f20373c83e79743a24633f1e9692bd4b5b10))

* feat: implement with-macros single indent ([`a739f72`](https://github.com/jnoortheen/xonsh-parser/commit/a739f72e8052f798657022d48123551113174950))

* feat: enable handling subproc macros ([`2f67e8c`](https://github.com/jnoortheen/xonsh-parser/commit/2f67e8c1ff856f9d979639a510d93efa59fbbf39))

* feat: handle parenthesis inside macros ([`b204689`](https://github.com/jnoortheen/xonsh-parser/commit/b2046890b25c60114b14c1a1985c0a74752924e4))

* feat: handle macro parameters with whitespace ([`9d72d91`](https://github.com/jnoortheen/xonsh-parser/commit/9d72d9197c528f92defc34e2be68f92a18bc725f))

* feat: tokenize whitespaces/Operators as their own Tokens instead of OP ([`2d20781`](https://github.com/jnoortheen/xonsh-parser/commit/2d20781deb58d7585ddf03cd44a726360c347099))

* feat: ability to accept hard keywords in macros

and sub-procs ([`72cdb16`](https://github.com/jnoortheen/xonsh-parser/commit/72cdb167f3babe5e171d022ba2c6bec699b439ea))

* feat: implement macros basic level ([`5637e97`](https://github.com/jnoortheen/xonsh-parser/commit/5637e97a4742c99b17e456c1ee292a1f146fee51))

* feat: make whole test suit pass or xfail ([`222c520`](https://github.com/jnoortheen/xonsh-parser/commit/222c520bfffe66f53f9e571379df3b5b886921db))

* feat: implement `&amp;&amp;`, `||` combinators ([`cde57db`](https://github.com/jnoortheen/xonsh-parser/commit/cde57db3e3a2df7b6cf12fefd8a3e1e0b5b53296))

* feat: implement path-search regexes ([`baa0f09`](https://github.com/jnoortheen/xonsh-parser/commit/baa0f09768a2a8c5cb408f5a3298f907f36d1ed4))

* feat: implement help? syntax ([`02b5165`](https://github.com/jnoortheen/xonsh-parser/commit/02b5165b488cc50ae8266ee2a53e6c0ab35523a3))

* feat: handle adjacent replacement and pass as *cmds

prefix/suffix to the $() ([`6ee7b5f`](https://github.com/jnoortheen/xonsh-parser/commit/6ee7b5f006ec2b5d1ea49891f9f11044dc8d0661))

* feat: implement @() - python-expr operator ([`c309d59`](https://github.com/jnoortheen/xonsh-parser/commit/c309d59b8dac39ccd979f9b1a12c483ec742132d))

* feat: implement @$() - subproc_injection ([`731e02a`](https://github.com/jnoortheen/xonsh-parser/commit/731e02a56f891ca8783c48f5129096e398646fb8))

* feat: implement !(), ![], $[] operators ([`8081eb6`](https://github.com/jnoortheen/xonsh-parser/commit/8081eb62248dc8c1fb39e4d49558ff271261e9d0))

* feat: implement splitting by WS/NL ([`fedc23f`](https://github.com/jnoortheen/xonsh-parser/commit/fedc23f4cfbe1607a5d61ae6d3a0c6c5feb1f9e9))

* feat: tokenize search-path ([`2b0972d`](https://github.com/jnoortheen/xonsh-parser/commit/2b0972d6230b2b633dae934cf0ee3589804c6689))

* feat: add $() handling simple cases ([`55063a7`](https://github.com/jnoortheen/xonsh-parser/commit/55063a7cea865b4f73036aa9ee12bb1267b08b23))

* feat: implement env names and env expressions

$env and ${expr} ([`8c18a6d`](https://github.com/jnoortheen/xonsh-parser/commit/8c18a6d5283050154d017f9b709d52a0666946ab))

* feat: tokenize xonsh operators separately

instead of returning token.OP ([`4d75c4e`](https://github.com/jnoortheen/xonsh-parser/commit/4d75c4ea7650d2e40435996016d04487266a0946))

* feat: support py311 &amp; py312

https://github.com/we-like-parsers/pegen/pull/95/files ([`c5e4f74`](https://github.com/jnoortheen/xonsh-parser/commit/c5e4f74d1c6f0de42a93e7fc1a7de32e635212b6))

* feat: add tokenize code for untokenizer from py312 stdlib ([`4b7bcda`](https://github.com/jnoortheen/xonsh-parser/commit/4b7bcda04048a2db9b0b2b9f38c86f5143185e76))

* feat: add fstring tokens from py3.12 ([`8426520`](https://github.com/jnoortheen/xonsh-parser/commit/8426520942e08f08e39f568410b6c3f38fc09d4b))

* feat: implement parsing $env vars ([`b5d8c0d`](https://github.com/jnoortheen/xonsh-parser/commit/b5d8c0ddcb0e6808d5782ca2628a2e353178b989))

* feat: make parser py39+ ([`c27828b`](https://github.com/jnoortheen/xonsh-parser/commit/c27828b19a3023f74e07501df0bc0b0790d5d46a))

* feat: handle tokens separately in generator ([`fe55745`](https://github.com/jnoortheen/xonsh-parser/commit/fe55745c33489d6110f6dd5912277b20c673344e))

* feat: handle loading ply parser ([`387519b`](https://github.com/jnoortheen/xonsh-parser/commit/387519bcc70bc16c2e210c526d0f3bb7c7725c85))

* feat: use taskfile.yml with source watch ([`b88ce44`](https://github.com/jnoortheen/xonsh-parser/commit/b88ce4427aef33954b514b88578c7591f4b9b132))

* feat: pass custom token set to PythonParserGenerator ([`506e3d1`](https://github.com/jnoortheen/xonsh-parser/commit/506e3d107793d1c1b21da35b69dca9916d574163))

* feat: add pegen from CPython/Tools ([`e8e36a7`](https://github.com/jnoortheen/xonsh-parser/commit/e8e36a7be465a7874a9d2d5283d3805a9dae863e))

* feat: handle env names in tokens ([`8eef67e`](https://github.com/jnoortheen/xonsh-parser/commit/8eef67ec5d6836f76d3ea80948aa5927540219b8))

* feat: implement path literals ([`4d30061`](https://github.com/jnoortheen/xonsh-parser/commit/4d30061331c9cef4e4c0b0573f279f68e980f85e))

* feat: simplify tokenize.py ([`64385ae`](https://github.com/jnoortheen/xonsh-parser/commit/64385aea43cd686f656bebf74d5d3868ee85607d))

* feat: include tests from xonsh ([`e3eee5d`](https://github.com/jnoortheen/xonsh-parser/commit/e3eee5dafacdca84af1fc235b3677064e8d19250))

* feat: use tokenizer from package ([`3ae4e26`](https://github.com/jnoortheen/xonsh-parser/commit/3ae4e26dffd97336e0363ee56c030ff7a40ce562))

* feat: add xonsh tokenize ([`584ad77`](https://github.com/jnoortheen/xonsh-parser/commit/584ad77665a130d6d952cd3505e9922800239651))

* feat: move towards custom tokenizer ([`e282596`](https://github.com/jnoortheen/xonsh-parser/commit/e282596c0f58765920fe3c688c7cb5b0b86d89fd))

* feat: add tests from pegen site ([`f7ab935`](https://github.com/jnoortheen/xonsh-parser/commit/f7ab93525a7ea693eb412fafda49903c445f25bb))

* feat: add pegen project files ([`c63ac43`](https://github.com/jnoortheen/xonsh-parser/commit/c63ac43d7b61652a439ca3302aa7cb177e73a258))

* feat: add peg_parser from parser ([`9c2958d`](https://github.com/jnoortheen/xonsh-parser/commit/9c2958d5f3c586bdd29fe14c395bb30dbc5eac00))

* feat: update tokenizer changes from xonsh v0.16.0 ([`3e654a2`](https://github.com/jnoortheen/xonsh-parser/commit/3e654a28daadad45fa202d6e656eb4bd6c266d85))

* feat: add mypyc pickle ([`b79ca3f`](https://github.com/jnoortheen/xonsh-parser/commit/b79ca3f62e63fcd92668191d1abb24daa958bbbb))

* feat: add mypyc compiled data format ([`6230653`](https://github.com/jnoortheen/xonsh-parser/commit/62306534fd20b557866373a8fff92359fd63bb20))

* feat: able to load multiple format lr-tables ([`c934f65`](https://github.com/jnoortheen/xonsh-parser/commit/c934f6514c3b1f0a6feb73c1705571b489997446))

* feat: add benchmark for different type of tables ([`001cb3f`](https://github.com/jnoortheen/xonsh-parser/commit/001cb3f48c6721be996b351e9a0ea0fc7e90e7f3))

* feat: exp-1 initial sizes ([`98ed879`](https://github.com/jnoortheen/xonsh-parser/commit/98ed879834ad01e5683c531f1ef3e308966e900b))

* feat: support to writing to Python lr-tables ([`2170de3`](https://github.com/jnoortheen/xonsh-parser/commit/2170de305ba7ccb91ad8a4c0c237a5c903ce76a7))

* feat: add tests from xonsh repo ([`306877c`](https://github.com/jnoortheen/xonsh-parser/commit/306877ce141696da95bb656b915bde9fdf6beee1))

* feat: add preprocessing based parser ([`cb19df4`](https://github.com/jnoortheen/xonsh-parser/commit/cb19df44278199e1951550afbe7396bd33ecc79d))

* feat: include tokenize_rt module from

https://github.com/asottile/tokenize-rt/blob/c2bb6f32371408c0490e817b6dd48285d804e36d/tokenize_rt.py ([`55f5d3e`](https://github.com/jnoortheen/xonsh-parser/commit/55f5d3ed7d2f8e9a29a6eb6f1867eeea6bf3af0f))

* feat: write python lr-table ([`e3746f0`](https://github.com/jnoortheen/xonsh-parser/commit/e3746f0c66defd5197169c9d544a3f61b689b224))

* feat: add execer from xonsh package ([`47b76f4`](https://github.com/jnoortheen/xonsh-parser/commit/47b76f4650e32301ce0e76232960483e6d17f5ff))

* feat: use setuptools as package builder ([`c61de1e`](https://github.com/jnoortheen/xonsh-parser/commit/c61de1e9ed9e69bd5a920745cb1f755b46606cf2))

* feat: optimize having actions/gotos as tuple instead of dict

unnecessarily dict was used as a container to hold int keys ([`fe1ee46`](https://github.com/jnoortheen/xonsh-parser/commit/fe1ee468ad7f130e06aaceae55417a6b223f0762))

* feat: improve type annotations ([`9ac82d2`](https://github.com/jnoortheen/xonsh-parser/commit/9ac82d271afeaf9aac299d68c3d2a4dfda886667))

* feat: tracemalloc benchmarking ([`1c30fed`](https://github.com/jnoortheen/xonsh-parser/commit/1c30fedc62abc9aad36abab98dc5ea350c8c0ad6))

* feat: the first optimization iteration worked

the parsing speed and memory usage ([`7e18907`](https://github.com/jnoortheen/xonsh-parser/commit/7e189079abc2c045ed22c9c3b25548ad0183f7a1))

* feat: optimize loading as pickle file v5 ([`34a01df`](https://github.com/jnoortheen/xonsh-parser/commit/34a01df7907cab409689e82ad9627c95609bef78))

* feat: add support for loading generated table ([`7201341`](https://github.com/jnoortheen/xonsh-parser/commit/72013415596744ad3e3bb37ce812d13d151a88cf))

* feat: add a function to write parser table as json ([`8a8f3f0`](https://github.com/jnoortheen/xonsh-parser/commit/8a8f3f0fed943446b68ea226b1c1efbe0dde1d65))

* feat: add benchmark to track parser size ([`5700928`](https://github.com/jnoortheen/xonsh-parser/commit/5700928e6694f6dbeed6009a7d5f27c6e4530185))

* feat: update to ply new format ([`16d5f5c`](https://github.com/jnoortheen/xonsh-parser/commit/16d5f5c871cf7dc9ff6ca0676331cd5679330895))

* feat: copy ply yacc from subtree ([`18ef242`](https://github.com/jnoortheen/xonsh-parser/commit/18ef242489b1d06dc472b7b322abe4f4ad43b109))

* feat: copy parser files from xonsh repo

commit: 12ab76e5359899efd51fa340ebc0c9a24bad3682 ([`ee24ec9`](https://github.com/jnoortheen/xonsh-parser/commit/ee24ec9cbecff3172fb23c4fbfe33ae0c0e77512))

### Fix

* fix: handle fstrings with newlines ([`6da8f1c`](https://github.com/jnoortheen/xonsh-parser/commit/6da8f1c200aea4dac857ef648270d55793e3a076))

* fix: remove duplicate annotated_rhs from CPython PR

https://github.com/python/cpython/pull/117004/files ([`95e0f68`](https://github.com/jnoortheen/xonsh-parser/commit/95e0f68493e1be1698802094d580763feeb44ac7))

* fix: update tests for the change in using enum tokens ([`12690cd`](https://github.com/jnoortheen/xonsh-parser/commit/12690cd79fda9a2e3c723ac77d3045d4720f6c97))

* fix: clash between proc and with macros ([`7f28ae8`](https://github.com/jnoortheen/xonsh-parser/commit/7f28ae8af242943254d6e90e10217ed160561921))

* fix: handle sub procs regression fails ([`f7ae053`](https://github.com/jnoortheen/xonsh-parser/commit/f7ae053c9a1b8fd9a0f2e2f6d56d32ec4d98766b))

* fix: import Target for del tests ([`ad81128`](https://github.com/jnoortheen/xonsh-parser/commit/ad811289981ff554c5c7a64240a08f3630bf2169))

* fix: store env variable case ([`8a74396`](https://github.com/jnoortheen/xonsh-parser/commit/8a7439685eb751cfc34f09e229173140c4d44d02))

* fix: implement parenthesis level for xonsh tokens ([`f1a36b1`](https://github.com/jnoortheen/xonsh-parser/commit/f1a36b1c761b58b1f2a7a0f3923d569f8d4421e9))

* fix: deprecation warning ([`8ee4720`](https://github.com/jnoortheen/xonsh-parser/commit/8ee472047887f5b0dbd16d2ab5698014186136d6))

* fix: deprecation warning ast.Str ([`7908f09`](https://github.com/jnoortheen/xonsh-parser/commit/7908f09621f17ebc52d6cd6c2a3932a26d4496df))

* fix: deprecation warning ast.Str ([`ecc96b7`](https://github.com/jnoortheen/xonsh-parser/commit/ecc96b7c2acb1f40380251306a692fede1e60160))

* fix: update tests of older versions than py39 ([`de3674c`](https://github.com/jnoortheen/xonsh-parser/commit/de3674c51d0fdff2f218df474de8d0f9f91b4e10))

* fix: exporting parser table as jsonl ([`de239da`](https://github.com/jnoortheen/xonsh-parser/commit/de239da65fbbb11e8e94580a094a2eabfde6fe99))

* fix: ply parser has to return None in case of failure ([`92d25bd`](https://github.com/jnoortheen/xonsh-parser/commit/92d25bd19d4faa0dcbcc5f9138f3ae1aa156abed))

* fix: tokenizing with correct lexpos ([`62c3f1f`](https://github.com/jnoortheen/xonsh-parser/commit/62c3f1fb4e5269c82f3744067ec15e420a8cd2e0))

* fix: the type returned after parse ([`c0ed347`](https://github.com/jnoortheen/xonsh-parser/commit/c0ed3473e17f06cb40fda3db35c2e4c833404307))

* fix: update tests ([`3976f97`](https://github.com/jnoortheen/xonsh-parser/commit/3976f9716a8195d859b72bb293b71aec040b0bb7))

* fix: type annotate the code fully ([`736622e`](https://github.com/jnoortheen/xonsh-parser/commit/736622e55ef2f876a18f828089106a675a4e0fb3))

* fix: update type hint import ([`ca9c53d`](https://github.com/jnoortheen/xonsh-parser/commit/ca9c53d1c232db1b4c63a6b07dafad591117e4a2))

* fix: ruff linter errors and disable mypy ([`0d1b772`](https://github.com/jnoortheen/xonsh-parser/commit/0d1b772dd8f421abc8553ede835681564eeec622))

### Refactor

* refactor: simplify token string handling ([`c75f977`](https://github.com/jnoortheen/xonsh-parser/commit/c75f97755b2b80848afb209d01efca3371d70eff))

* refactor: update tokenizing WS and simplify psuedo match ([`6c245fa`](https://github.com/jnoortheen/xonsh-parser/commit/6c245fa7c6384ec8d922121199d4cbf3858afef4))

* refactor: mark symbols with single quotes ([`9c7b2a3`](https://github.com/jnoortheen/xonsh-parser/commit/9c7b2a3a167951fa6220deff2159d708f4cc934e))

* refactor: use symbols directly in grammar spec for clarity ([`cf5e6ce`](https://github.com/jnoortheen/xonsh-parser/commit/cf5e6ce6cd08da2b662c81741eaa516ecd2efe1c))

* refactor: restructure the code

make pegen the main ([`1975bd6`](https://github.com/jnoortheen/xonsh-parser/commit/1975bd6193cbe8340373ed3c34c13d4e384cef72))

* refactor: move tasks out ([`05c80ad`](https://github.com/jnoortheen/xonsh-parser/commit/05c80adf3fac0e55e19902a654b1accfae9ee727))

* refactor: cleanup functions ([`2c69ae0`](https://github.com/jnoortheen/xonsh-parser/commit/2c69ae025f2ca0dba49ab5e34b4aa34b06af431c))

* refactor: handle OP tokens separately

as exact_token_types ([`422bcde`](https://github.com/jnoortheen/xonsh-parser/commit/422bcde7bb453f89034e272136dc2746b938bcdf))

* refactor: code cleanup ([`19337a8`](https://github.com/jnoortheen/xonsh-parser/commit/19337a80944956a71579cabea9c9263e7bc599cb))

* refactor: cleanup tokenizer ([`b80380f`](https://github.com/jnoortheen/xonsh-parser/commit/b80380f0b62a211ce1cfbb5b5e50e16a63259399))

* refactor: update tokenizer ([`fae1b5a`](https://github.com/jnoortheen/xonsh-parser/commit/fae1b5ae3711f4bf0dc2f6f7ce1acfb741eefb31))

* refactor: enable more ruff plugins ([`244248a`](https://github.com/jnoortheen/xonsh-parser/commit/244248af58ff3590dd62c79d2035315523f961d7))

* refactor: update ${..} handling ([`f679334`](https://github.com/jnoortheen/xonsh-parser/commit/f6793347f1d54d23386ab7a1413316f5d637da26))

* refactor: move tests out of package ([`5ed245e`](https://github.com/jnoortheen/xonsh-parser/commit/5ed245e8ccc4161793e6faa4988f22323f0f20bf))

* refactor: update xonsh token names ([`3274008`](https://github.com/jnoortheen/xonsh-parser/commit/32740084209910f53524267cedbaa853cef9ca69))

* refactor: simplify tokenize.py further

- remove bytes handling
- move contstr handling to its own function ([`e7380e7`](https://github.com/jnoortheen/xonsh-parser/commit/e7380e79e8ee7de691aeb9070c2a09ac0f5060a4))

* refactor: simplify tokenize.py with states ([`29133e0`](https://github.com/jnoortheen/xonsh-parser/commit/29133e0d12102a9e9ec45ecca2144bb9d4be2e9b))

* refactor: move untokenize to its own module ([`8396d1c`](https://github.com/jnoortheen/xonsh-parser/commit/8396d1c6a6431b56d4ac09f9d6a7501a33301143))

* refactor: remove ply based parser dir ([`a18b823`](https://github.com/jnoortheen/xonsh-parser/commit/a18b823d74282fd82e575822a2134a627f31bd23))

* refactor: make parser py39+ and optimize imports ([`8a94ca2`](https://github.com/jnoortheen/xonsh-parser/commit/8a94ca28280dc38f8a72b52345dc372d3edf6d8f))

* refactor: adding from we-like-parsers/pegen ([`93fae9e`](https://github.com/jnoortheen/xonsh-parser/commit/93fae9ef352c96ac1d57c2912ea694496de19495))

* refactor: adding from we-like-parsers/pegen ([`7f8d9a3`](https://github.com/jnoortheen/xonsh-parser/commit/7f8d9a3a19b34737a7244f3f87115aa8a6ab2c75))

* refactor: move parse methods to class ([`05edb2a`](https://github.com/jnoortheen/xonsh-parser/commit/05edb2af5cf4bcd92fd9eff34d7ce7ae47a1880d))

* refactor: move ply tests ([`087dbeb`](https://github.com/jnoortheen/xonsh-parser/commit/087dbeb4bb2d3644ff32a23a1c81d9e11f1c1fb9))

* refactor: update tokenizer code ([`3b2268b`](https://github.com/jnoortheen/xonsh-parser/commit/3b2268b3512a31c0474724d59fbf5b5d1a9997e2))

* refactor: copy tokenize from python stdlib v310 ([`2f51788`](https://github.com/jnoortheen/xonsh-parser/commit/2f517889adf89a31f0dfb5ae4d42253f55d70158))

* refactor: move tokens ([`f9e1d4d`](https://github.com/jnoortheen/xonsh-parser/commit/f9e1d4dbd489fabf31d1cdc759804890f6d18656))

* refactor: ruff style ([`f96462e`](https://github.com/jnoortheen/xonsh-parser/commit/f96462ef1782555df701be11d58af307975195cd))

* refactor: overwrite header ([`40ba0a9`](https://github.com/jnoortheen/xonsh-parser/commit/40ba0a9bdfc60a838e1c9f5a6a766c9b8930a118))

* refactor: accept str path to load parser ([`a36dfe8`](https://github.com/jnoortheen/xonsh-parser/commit/a36dfe8b426f70a7a435a3256ea4ad12dc0aeab6))

* refactor: merge overridden actions to base class ([`ba48b11`](https://github.com/jnoortheen/xonsh-parser/commit/ba48b110adfd8636d6a7ec9696b7b603718b898a))

* refactor: use unparse to test parsing ([`bbe4043`](https://github.com/jnoortheen/xonsh-parser/commit/bbe404344ad3de8bcc0390cef700f2608372ac5d))

* refactor: generate docstring dynamically

instead of creating functions multiple times during runtime ([`b8be353`](https://github.com/jnoortheen/xonsh-parser/commit/b8be3533db99f149c81b05474123efedecc41bbc))

* refactor: improve typing of ply lrparser module ([`2fea65d`](https://github.com/jnoortheen/xonsh-parser/commit/2fea65dd2142124dcb5288856f5964f3b8d1cf3b))

* refactor: type lexer and parser modules ([`bf10aaa`](https://github.com/jnoortheen/xonsh-parser/commit/bf10aaa8623589c7e099a668e24e246d96ba30f9))

* refactor: option to debug parser generation ([`41a3345`](https://github.com/jnoortheen/xonsh-parser/commit/41a33458bcfc55cb4fa78ff4b26186e2f00d4e28))

* refactor: update to fstring from sly ([`8173021`](https://github.com/jnoortheen/xonsh-parser/commit/817302131b7d77a6257f75893d1d8f088650410b))

* refactor: update sample usage ([`47de232`](https://github.com/jnoortheen/xonsh-parser/commit/47de2322fc210a1cd4640a9bd8205f2c8a47fae2))

* refactor: Yaccsymbol.slots ([`058ec50`](https://github.com/jnoortheen/xonsh-parser/commit/058ec5027534b488f2bf48e3b99d94fcacb3f7f8))

* refactor: update benchmark time function ([`3c81a59`](https://github.com/jnoortheen/xonsh-parser/commit/3c81a5957d42bb2b748b6e8754537211a6d953c5))

* refactor(ply): split table generator and loader

to optimize the loading time. generating is mostly done one time ([`273df2b`](https://github.com/jnoortheen/xonsh-parser/commit/273df2b6a90f1d95582370bffbc570bee580bbae))

* refactor(ply): remove unused global variable ([`223127a`](https://github.com/jnoortheen/xonsh-parser/commit/223127a0415d1b34fedddbb30b40ee6b73f9136d))

* refactor: return class so options can be passed ([`5507cbc`](https://github.com/jnoortheen/xonsh-parser/commit/5507cbc943255d9dd2f9c1bcf1ceffd7ffaa2c1c))

* refactor: update imports and functions missing from xonsh ([`b49c22e`](https://github.com/jnoortheen/xonsh-parser/commit/b49c22e13a0b74047a4ffbd3dea46e334f10cb7a))

* refactor: update lexer functions from xonsh.tools ([`066c78e`](https://github.com/jnoortheen/xonsh-parser/commit/066c78eb73dbc48ea9035189f431a42c94df27eb))

### Style

* style: update benchmark file ([`63e1d5d`](https://github.com/jnoortheen/xonsh-parser/commit/63e1d5d160d3d610c9cbc26505f254f2b848c277))

* style: add annotations to lexer ([`c567d7c`](https://github.com/jnoortheen/xonsh-parser/commit/c567d7c6de801bbc7a5a7d5605acf980c9262981))

### Test

* test: update fstring tests with xonsh symbols ([`c7679d4`](https://github.com/jnoortheen/xonsh-parser/commit/c7679d4338bd7b619005c837e73ba39694291867))

* test: parameterize test cases ([`007deb5`](https://github.com/jnoortheen/xonsh-parser/commit/007deb532ad02c4d123f4fe6f86262525aefb36f))

* test: rename file ([`3802dde`](https://github.com/jnoortheen/xonsh-parser/commit/3802dde67ebca788c0df56df81be59a9438c7d0e))

* test: update tests ([`e25b7e7`](https://github.com/jnoortheen/xonsh-parser/commit/e25b7e77e2e55e44cdb52631ff83c7934a43f834))

* test: more passing tests ([`1ea9327`](https://github.com/jnoortheen/xonsh-parser/commit/1ea93279741f597b5ea10dff77309b40db4508f9))

* test: changes in lexer tests operator token handling change ([`f0f74cf`](https://github.com/jnoortheen/xonsh-parser/commit/f0f74cf5e366e708b8cb0467398a27ba1eafaef9))

* test: now test_invalid works ([`cb95266`](https://github.com/jnoortheen/xonsh-parser/commit/cb9526673045c44ee3e7d7445915a0ba8f05313b))

* test: post verbose parser output upon first 3 fails ([`396e304`](https://github.com/jnoortheen/xonsh-parser/commit/396e3046a589abc03bb46d074dfd7cb7a5ffb6e1))

* test: organize tests data ([`a5ef7db`](https://github.com/jnoortheen/xonsh-parser/commit/a5ef7dbf757b38529c5c34d2f335e503dfee6db6))

* test: organize tests ([`d76ba9e`](https://github.com/jnoortheen/xonsh-parser/commit/d76ba9eb036347cdff96b0ed0cffd2d7ca916884))

* test: tidy test cases ([`46a91af`](https://github.com/jnoortheen/xonsh-parser/commit/46a91af9f0d5211dbe106a014dd0083d6540ba55))

* test: fix test data ([`337213b`](https://github.com/jnoortheen/xonsh-parser/commit/337213bb0963d0566568932f0d46e75e938bdbbe))

* test: update parser tests ([`d66124a`](https://github.com/jnoortheen/xonsh-parser/commit/d66124adbfc86d77f49b4995e3e39195ff5582ce))

* test: move test cases to files

and split big test_parser.py ([`e85b333`](https://github.com/jnoortheen/xonsh-parser/commit/e85b333825049bdc2bfd366373d831b3609808d3))

* test: remove pure python tests

as it is already covered in tests/test_ast_parsing.py ([`b5fe044`](https://github.com/jnoortheen/xonsh-parser/commit/b5fe0448a5d9bf5d1450ca6a48de94e79dd01bad))

* test: update tests for the tokenizer ([`a06b9f4`](https://github.com/jnoortheen/xonsh-parser/commit/a06b9f4e211f14d9eca8d701b03c6fc7a7b92131))

* test: update tests to mark xfail xonsh tokens ([`bf7c697`](https://github.com/jnoortheen/xonsh-parser/commit/bf7c69731c1bde60385971541fce351cfbdb3969))

* test: fix test errors/fails of missing fixtures ([`f52eaf9`](https://github.com/jnoortheen/xonsh-parser/commit/f52eaf986a2f19612b794b8c0de97bd44e0f50d4))

* test: update tests and fix mypy errors ([`4a6dbd6`](https://github.com/jnoortheen/xonsh-parser/commit/4a6dbd669e2e8dc8ed595c1726dcec5d47b61370))

* test: rerun parse if previous failed ([`b41e315`](https://github.com/jnoortheen/xonsh-parser/commit/b41e3156e253c29263bfa86c0a3ffb0e4f13fef4))

* test: update tests to use own tokenizer ([`8c2c4d1`](https://github.com/jnoortheen/xonsh-parser/commit/8c2c4d190b33bbb1d83f36013634d6685dabc8e8))

* test: add pre-processor based tests ([`def09e6`](https://github.com/jnoortheen/xonsh-parser/commit/def09e6b0654957c1b85d9c9fb5ed444dd58eb43))

* test: add test files from xonsh repo ([`deca176`](https://github.com/jnoortheen/xonsh-parser/commit/deca17623aade6865f112daa4ba78fb23940281e))

* test: rename basic sanity tests ([`190a0ea`](https://github.com/jnoortheen/xonsh-parser/commit/190a0eaf33f53d9121521ab7ac1c62993b684a0a))

* test: update sample test ([`5898e7b`](https://github.com/jnoortheen/xonsh-parser/commit/5898e7b1de96095da1388125140f62103a99e6da))

* test: xfail xonsh session dependent tests ([`8f8367a`](https://github.com/jnoortheen/xonsh-parser/commit/8f8367a14677233021e551e6759cf64d07c36764))

* test: make ast tests pass ([`8becc23`](https://github.com/jnoortheen/xonsh-parser/commit/8becc23b346641c3ca8575e240a25608695cc626))

* test: split parser tests ([`050aaee`](https://github.com/jnoortheen/xonsh-parser/commit/050aaeedf7f1dacc7bd4d481c647e14ce92e364a))

* test: add test files from xonsh repo ([`c300165`](https://github.com/jnoortheen/xonsh-parser/commit/c3001653c3d42fee18ae4a791004692bdd22c523))

* test: add invalid state ([`7bebe43`](https://github.com/jnoortheen/xonsh-parser/commit/7bebe43f889f4b3eaff31ced3215304d1d98b5a1))

### Unknown

* style: ([`2261960`](https://github.com/jnoortheen/xonsh-parser/commit/2261960524021c9d3f7026550c1086dd805437d6))

* docs: ([`0b90415`](https://github.com/jnoortheen/xonsh-parser/commit/0b904150b0afa9b553ab41f4d67ddc4c9cf4d78d))
