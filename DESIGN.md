# `pygments-pss` — Design Document

**Status:** Reviewed 2026-08-13; §12 decisions accepted
**Target:** Accellera PSS 3.1 (Draft 19, 2026-07-14) + earlier revisions
**Author:** initial draft

---

## 1. Purpose and scope

Pygments ships no lexer for the Accellera Portable Test and Stimulus Standard. Every
consumer of PSS source in a documentation or publishing pipeline therefore either
renders PSS as plain text or hand-rolls a lexer. At least one hand-rolled lexer already
exists in this stack (`sphinx-pss/src/sphinx_pss/lexer.py`), and more will accumulate.

`pygments-pss` is a standalone, installable Pygments **plugin package** providing a PSS
lexer that registers itself through the `pygments.lexers` entry point. Once installed,
`pygmentize -l pss`, `get_lexer_by_name("pss")`, Sphinx `.. code-block:: pss`, MkDocs
` ```pss `, and `guess_lexer_for_filename("x.pss")` all work with no further
configuration.

### Goals

- G1. Highlight PSS 3.x source correctly, including 3.1 additions (annotations,
  monitors, behavioral coverage, triple-quoted strings with template notation).
- G2. Zero runtime dependencies beyond Pygments itself. No parser, no ANTLR, no C++.
- G3. Tolerate *fragments*. Documentation shows snippets, not compilation units; the
  lexer must never depend on seeing a `package` or a balanced brace.
- G4. Be the single source of PSS highlighting for the psstools stack — `sphinx-pss`
  drops its private copy and depends on this package.
- G5. Keep the keyword vocabulary mechanically synchronized with an authoritative
  source rather than hand-maintained.
- G6. Be structured so it could be contributed to Pygments core later with minimal
  change (see §11).

### Non-goals

- N1. Parsing, semantic analysis, or error detection. A syntax error must degrade to
  plausible highlighting, never to a cascade of `Token.Error`.
- N2. A Pygments *style*. PSS is a C-family language; existing styles are appropriate.
- N3. A language server, formatter, or indexer.
- N4. Highlighting non-PSS artifacts (PSS-generated C/SV output) as a first-class
  feature — but see §6.4 for target-template embedding.

---

## 2. Context and prior art

| Source | Role in this design |
| --- | --- |
| `PSS 3.1 Draft 19 2026.07.14 clean.md` (in-repo) | Normative lexical conventions (Clause 4), keyword table (Table 3), grammar (Annex B), core library (Annex C). Note: it is an in-development draft and carries `MantisNNNN` change tags inline. |
| `pssparser/src/PSSLexer.g4` | Machine-readable token list from a working PSS front end. The practical vocabulary source. |
| `sphinx-pss/src/sphinx_pss/lexer.py` | Existing working lexer; the starting point for the implementation and the consumer to migrate. |
| `pygments/pygments-plugin-scaffolding` | Upstream's recommended plugin package template. |
| `pygments/lexers/hdl.py` (`SystemVerilogLexer`) | Closest built-in analogue; source of idioms for sized literals and C-family structure. |

**Relationship to `sphinx-pss`.** `sphinx-pss` currently defines `PssLexer` and calls
`app.add_lexer("pss", PssLexer)` in its `setup()`. After this package lands, `sphinx-pss`
depends on `pygments-pss` and imports the lexer from here. It should *keep* the
`app.add_lexer` call — it is harmless when the entry point already resolves, and it
keeps behavior deterministic if a user has plugin discovery disabled
(`get_lexer_by_name(..., plugins=False)`) or an unusual install layout.

---

## 3. Vocabulary: what the LRM actually says

Facts extracted from the draft LRM, which drive §6.

**Clause 4.1 — Comments.** `/* … */` and `//` to end of line. No nesting.

**Clause 4.2 — Identifiers.** `[A-Za-z_][A-Za-z0-9_]*`, case-sensitive.

**Clause 4.3 — Escaped identifiers.** Start with `\`, contain any printable
non-whitespace ASCII (0x21–0x7E), and terminate at whitespace. `\busa+index`,
`\net1/\net2`, `\{a,b}` are all single identifiers. **This is the one lexical rule most
likely to be missing from a naive C-family lexer**, and getting it wrong turns a line
into operator soup.

**Clause 4.4 — Keywords.** Table 3, 114 entries. See §3.1 for defects found.

**Clause 4.6 — Numbers.**
- `bin_number ::= 0[bB] bin_digit {bin_digit|_}`
- `oct_number ::= 0 {oct_digit|_}` — a leading `0` makes it octal
- `dec_number ::= [1-9] {dec_digit|_}`
- `hex_number ::= 0[xX] hex_digit {hex_digit|_}`
- Based literals: `[size] ' [sS] (b|B|o|O|d|D|h|H) digits`, e.g. `4'sd12`, `'d12`,
  `8'hFF`. Size is an unsigned non-zero decimal. Whitespace may separate the base
  character from the digits (the LRM permits it; we will *not* support the split form —
  see §12 D4).
- Floats: `unsigned . unsigned` (digits required on **both** sides) or scientific
  `unsigned [. unsigned] [eE] [+-] unsigned`. `20 .15` is explicitly illegal.
- `_` is legal anywhere but first.

**Clause 4.7 — String literals.**
- `QUOTED_STRING`: `"…"`, printable ASCII only, single line, escapes
  `\' \" \? \\ \a \b \f \n \r \t \v \ddd` (exactly three octal digits).
- `TRIPLE_QUOTED_STRING`: `"""…"""`, any ASCII including newlines, **no escape
  character**.
- **4.7.1 Special elements in triple-quoted strings (3.1, Mantis8730/8356):**
  - Mustache expressions: `{{ expression }}`
  - Control-flow directives: `{% if (expr) %}`, `{% foreach … %}`, `{%%}` (close)

  These are PSS expressions embedded in string content and are a real highlighting
  opportunity — a target template is mostly opaque text with a few live PSS expressions
  in it.

**Annex B.18 — Operators.**
- Unary: `- ! ~ & | ^`
- Binary: `* / % + - << >> == != < <= > >= || && | & ^ **`
- Assignment: `= += -= <<= >>= |= &=`
- Ternary `? :`; range `..`; membership `in`; scope `::`; member `.`
- From `PSSLexer.g4` additionally: `->` (implication), `:=` and `:/` (dist weights),
  `...` (varargs, as in `type... args`), `@` (annotation), `#`.

**Annex B.5 — Exec blocks.**
```
exec_block            ::= exec exec_kind { { exec_stmt } }
target_code_exec_block::= exec exec_kind language_identifier = [tag :] string_literal ;
target_file_exec_block::= exec file filename_string = [tag :] string_literal ;
exec_kind             ::= pre_solve | post_solve | pre_body | body | header
                        | declaration | run_start | run_end | init_down | init_up
```
`language_identifier` is an identifier; `executor_pkg::target_language_e` enumerates
`C`, `CPP`, `SV`.

**Annex B.6/§7 — Annotations (3.1, Mantis8360).**
```
annotation_declaration ::= annotation annotation_identifier [ : type_identifier ] { … }
annotation             ::= @ annotation_type_identifier [ { .field = const_expr , … } ]
```
Applied as an element annotation (no semicolon) or standalone (`@desc_c {…};`).

**Annex C — Core library.** Packages `std_pkg`, `executor_pkg`, `addr_reg_pkg`,
`sync_pkg`. Includes `format`, `print`, `message`, `error`, `fatal`, `urandom`,
`urandom_range`, `file_open`/`file_close`/`file_write`/`file_read`/`file_exists`/
`file_write_lines`/`file_read_lines`, the float math set (`log`, `sqrt`, `pow`, `sin`,
…), `float_mantissa`/`float_exponent`/`float_sign`/`to_float`, types
`endianness_e`, `packed_s`, `sizeof_s`, `message_verbosity_e`, `file_handle_t`,
`file_option_e`, `float_base_s`, `float32_s`, `float64_s`, `executor_c`,
`executor_base_c`, `executor_group_c`, `executor_claim_s`, `target_language_e`,
`addr_space_base_c`, `contiguous_addr_space_c`, `transparent_addr_space_c`,
`addr_claim_s`, `addr_handle_t`, `alloc_*_mode_e`, `reg_access`, `node_s`, and more.

### 3.1 Defects found in the draft's keyword table

Diffing Table 3 against `PSSLexer.g4`:

| Word | Table 3 | `PSSLexer.g4` | Disposition |
| --- | --- | --- | --- |
| `annotation` | **absent** | present | Real 3.1 keyword (`annotation_declaration` in Annex B). Table 3 is out of date. Treat as keyword. |
| `numeric` | ambiguous — appears as mangled `numericMantis8389` text adjacent to an empty cell in the alphabetically correct slot | present | Not standard until proven otherwise: excluded from `dialect="std"`, included in `dialect="pssparser"` (§12 D1). |
| `pre_body` | present | absent | Grammar has it (`exec_kind`). Parser lags. Treat as keyword. |
| `this` | present | absent | Treat as keyword. |
| `from`, `init`, `option`, `pyimport`, `pyobj` | absent | present | `pssparser` extensions / legacy. Not standard. See §6.6. |
| `mutable` | absent | absent | Present in the current `sphinx-pss` lexer. **Not a PSS keyword — drop it.** |

The table itself is also visibly damaged by the PDF→Markdown conversion (cells shifted
across row boundaries), so it is *not* a trustworthy machine-readable source. Annex B
and `PSSLexer.g4` are.

---

## 4. Package design

### 4.1 Layout

```
pygments-pss/
├── pyproject.toml
├── ivpm.yaml                     (already present; §4.4)
├── README.md
├── LICENSE                       (Apache-2.0, already present)
├── DESIGN.md                     (this file)
├── .github/
│   └── workflows/ci.yml          test + publish (§4.4)
├── src/
│   └── pygments_pss/
│       ├── __init__.py           re-exports PSSLexer, __version__
│       ├── __version__.py        BASE/SUFFIX, as in pssparser (§4.4)
│       ├── lexer.py              PSSLexer
│       ├── _keywords.py          GENERATED — do not edit
│       └── py.typed
├── scripts/
│   └── gen_keywords.py           regenerates _keywords.py (§5)
└── tests/
    ├── conftest.py
    ├── corpus/                   *.pss files (§8.1)
    ├── snippets/                 *.pss + *.txt golden token dumps (§8.2)
    ├── test_no_error_tokens.py
    ├── test_snippets.py
    ├── test_entry_point.py
    └── test_vocabulary_sync.py
```

`src/` layout so tests exercise the installed package (and therefore the entry point),
not the working tree.

### 4.2 `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pygments-pss"
description = "Pygments lexer for the Accellera Portable Test and Stimulus Standard (PSS)"
requires-python = ">=3.9"
dependencies = ["Pygments>=2.14"]
license = "Apache-2.0"
keywords = ["pygments", "lexer", "pss", "accellera", "verification", "eda"]
classifiers = [
  "Topic :: Text Processing :: Filters",
  "Topic :: Software Development :: Documentation",
]
dynamic = ["version"]

[project.urls]
Homepage = "https://accellera.org/downloads/standards/portable-stimulus"
Source = "psstools/pygments-pss"   # self-hosted; see §4.4

[project.entry-points."pygments.lexers"]
pss = "pygments_pss.lexer:PSSLexer"
```

Notes:

- The entry-point *name* (`pss`) is cosmetic for lexers — Pygments calls
  `entrypoint.load()` and reads the class's own `aliases`/`filenames`/`mimetypes`.
  Formatters and styles are the ones where the name matters.
- **Pygments floor `>=2.14`.** Rationale: `Lexer.url` (2.9+) and stable
  `importlib.metadata`-based plugin discovery. If we set `version_added` (see §4.3) we
  should confirm no older Pygments chokes on the unknown attribute — it does not, it is
  a plain class attribute. 2.14 is a conservative floor that predates every currently
  supported Python's typical pin. Revisit if it blocks anything.

### 4.3 Lexer class metadata

```python
class PSSLexer(RegexLexer):
    name = "PSS"
    aliases = ["pss", "portable-stimulus"]
    filenames = ["*.pss"]
    mimetypes = ["text/x-pss"]
    url = "https://accellera.org/downloads/standards/portable-stimulus"
    version_added = ""          # empty for out-of-tree; set on upstreaming
```

`aliases[0]` must be `pss` — that is what every existing `.. code-block:: pss` and
` ```pss ` fence in the ecosystem already uses.

**Class name.** `PSSLexer`, not `PssLexer`. Pygments' own convention is `SystemVerilogLexer`,
`VHDLLexer`, `HTMLLexer` — acronyms stay upper. `sphinx-pss` uses `PssLexer`; we export
`PssLexer = PSSLexer` as a deprecated alias to make its migration a one-line change.

### 4.4 Repository, versioning, and publishing

The repository is **`psstools/pygments-pss`** on the self-hosted Forgejo instance
(`https://git.dvkit.org/psstools/pygments-pss`), alongside `pssparser` and `sphinx-pss`.
It publishes to PyPI **the same way `pssparser` does** (§12 D6), which fixes the
following:

- **Versioning.** `src/pygments_pss/__version__.py` follows the `pssparser` pattern:
  a `BASE` string, an empty `SUFFIX` that CI stamps with `.$GITHUB_RUN_ID`, and a
  `get_version()` that appends `git describe` output in a source tree. `pyproject.toml`
  takes `version` from it dynamically. This gives every CI build a unique, monotonically
  increasing dev version without hand-editing.
- **CI.** `.github/workflows/ci.yml` with a test job and a `publish` job gated on
  `github.event_name == 'push'` and the default branch, using
  `pypa/gh-action-pypi-publish@release/v1` with `secrets.PYPI_API_TOKEN` and
  `skip-existing: true`.
- **Simplifications versus `pssparser`.** This package is pure Python, so there is no
  ANTLR/CMake/Ninja build, no `manylinux` container, no `auditwheel` repair, and no
  per-interpreter wheel matrix — one `python -m build` produces a single universal
  wheel plus sdist. The test matrix still spans the interpreters `pssparser` supports
  (§8.5).
- **Branch name.** `pssparser` gates publishing on `master`; this repository's default
  branch is `main`. The publish condition must reference `refs/heads/main`.
- **`ivpm.yaml`.** Already present with an empty `default-dev` dep set. It gains the
  development dependencies (`pytest`, `pygments`) and, for the vocabulary generator
  (§5), a source dependency on `pssparser` so `PSSLexer.g4` is fetchable in a clean
  checkout. That dependency is **development-only** — it must not appear in
  `[project].dependencies`, since `_keywords.py` is generated and checked in.

---

## 5. Vocabulary sourcing and drift control

Hand-maintained keyword lists rot. The design keeps them generated.

`scripts/gen_keywords.py` reads `PSSLexer.g4` (from the `ivpm`-fetched `pssparser`
source under `packages/`, overridable by env var or `--grammar`) and emits
`src/pygments_pss/_keywords.py` containing frozen tuples plus a provenance header
recording the source file's git SHA and the LRM revision the classification was reviewed
against.

The *classification* (which bucket each keyword falls into — §6.2) is **not** derivable
from the grammar and lives in a hand-curated mapping inside the generator. New keywords
appearing in the grammar that the mapping does not classify cause the generator to fail
loudly rather than silently defaulting to `Keyword`.

`tests/test_vocabulary_sync.py` re-runs the generator in-memory and asserts the checked-in
`_keywords.py` matches. CI therefore fails when `pssparser` gains a keyword we have not
classified — the same guard-test idea `sphinx-pss` already uses for its upstream
assumptions.

Words the generator explicitly *adds* on top of the grammar, with justification recorded
in the mapping: `pre_body`, `this` (in the LRM, missing from `pssparser`).

---

## 6. Lexer design

### 6.1 Approach: `RegexLexer`

A `RegexLexer` state machine, not a wrapper over `pssparser`. Rationale: G2 (no
dependency), G3 (fragments must lex), speed, and the fact that Pygments' contract is
token-stream-over-arbitrary-text, which a real parser cannot satisfy.

### 6.2 Keyword taxonomy → token types

Every reserved word maps to exactly one token type. This is the part reviewers should
scrutinize, because it determines what the reader's eye picks out.

| Bucket | Token | Members |
| --- | --- | --- |
| **Type-declaring** | `Keyword.Declaration` | `action annotation buffer class component covergroup enum monitor package resource state stream struct typedef` |
| **Built-in types** | `Keyword.Type` | `array bit bool chandle float32 float64 int list map set string void` |
| **Modifiers/qualifiers** | `Keyword.Declaration` | `abstract atomic const dynamic export extend import instance override private protected public pure rand ref static symbol target solve type` |
| **Literals** | `Keyword.Constant` | `true false null` |
| **Pseudo-variables** | `Name.Builtin.Pseudo` | `this super` |
| **Control flow** | `Keyword` | `break continue do else foreach if match repeat return while` |
| **Activity / scheduling** | `Keyword` | `activity concat eventually forall join_branch join_first join_none join_select overlap parallel replicate schedule select sequence yield` |
| **Constraints** | `Keyword` | `constraint default disable dist forall if iff in unique with` |
| **Coverage** | `Keyword` | `bins cover coverpoint cross ignore_bins illegal_bins` |
| **Flow objects / resources** | `Keyword` | `bind in inout input lock output pool share` |
| **Exec** | `Keyword` | `exec body declaration file header init_down init_up post_solve pre_body pre_solve run_end run_start` |
| **Functions** | `Keyword` | `function` |
| **Conditional compilation** | `Comment.Preproc` | `compile has assert` — **only** in the sequences `compile if`, `compile has`, `compile assert` (see §6.3) |
| **Other** | `Keyword` | `as randomize` |

Words appearing in two buckets (`if`, `in`, `forall`, `default`, `file`) are context-free
in a `RegexLexer` — they get one token type, chosen from the row where the reader most
benefits. `if` → `Keyword`. `file` → `Keyword`.

**Core-library names** (§3, Annex C) → `Name.Builtin`, for both functions and types:
they are library, not language, so `Keyword.Type` would overstate them. Gated behind a
lexer option (§6.7) so users who dislike it can turn it off; **default on**, because
`urandom()` and `std_pkg::print()` reading as builtins is genuinely useful in
documentation.

### 6.3 State machine

```
root
├── whitespace, comments
├── conditional-compilation triples   (compile if / compile has / compile assert)
├── annotations                       @name  →  annotation-params
├── strings                           """ → tqstring;  " → string
├── numbers                           based, hex, bin, octal, float, decimal
├── escaped identifiers               \…  up to whitespace
├── keyword-then-name declarations    (§6.5)
├── keywords                          (words(), longest-first within a words() set)
├── qualified names                   ident ::  → Name.Namespace
├── function calls                    ident (  → Name.Function
├── identifiers
├── punctuation, operators
```

Sub-states: `comment-block`, `comment-docblock`, `string`, `tqstring`, `tqexpr`
(mustache), `tqdirective` (`{% … %}`), `annotation-params`.

**Ordering constraints that must hold** (each gets a snippet test):

1. Based literals (`4'sd12`, `'hFF`) before the `'` of anything else and before plain
   decimals, or `4` and `'sd12` split.
2. `0x…`/`0b…` before the octal rule, or `0` lexes alone and `x1F` becomes a name.
3. Float before integer, so `1.5` is not `1` `.` `5`.
4. Escaped identifiers before operators, or `\busa+index` shatters.
5. Longer keywords before shorter prefixes — `init_down` before any `init`,
   `join_branch` before `join_*` alternatives. `words()` sorts by length internally, but
   only *within one* `words()` call; keywords split across buckets must not prefix each
   other. Current buckets are safe; the generator asserts it.
6. `//` and `/*` before the `/` operator.
7. `"""` before `"`.

### 6.4 Strings, triple-quoted strings, and target templates

Plain strings: `String.Double`, with `String.Escape` for the LRM's exact escape set and
`Error` for an escape not in the table (the LRM says it is illegal). Newline inside a
quoted string is illegal; we terminate the string state at the newline rather than
running away — a runaway string is the single ugliest failure mode in a docs page.

Triple-quoted strings: `String.Heredoc` (Pygments' conventional token for
multi-line/templated string bodies), with **no** escape processing, plus:

- `{{ … }}` → `String.Interpol` delimiters, contents lexed as PSS expression tokens
  (`using(this, state="expr")`).
- `{% … %}` → `Comment.Preproc` delimiters, contents lexed as PSS.

**Target-language embedding (optional, phase 2).** For
`exec body C = """ … """;` we know the target language from the `language_identifier`.
A `bygroups` callback can capture it and dispatch the string body to `CLexer`,
`CppLexer`, or `SystemVerilogLexer` via `DelegatingLexer`-style `using()`. This is
genuinely nice for PSS documentation, where exec bodies are often the interesting part.

Risks: mustache/directive elements are PSS, not C, so a naive delegate mangles them;
and it pulls three more lexers into the import graph. **Decided (§12 D2): implement it
behind the `target_lexers` option, shipped off through phases 1–2; evaluate against the
corpus and flip the default to on in phase 3 only if it proves lossless.**

### 6.5 Declaration-name highlighting

`(action|component|struct|…)\s+(name)` → the name gets `Name.Class`. Retained from the
existing `sphinx-pss` lexer; in a documentation page the declared name is exactly what a
reader scans for. `exec` and `activity` are excluded because their operand is another
keyword or a brace, not a user name.

Extensions to the existing behavior:

- `function` → the name gets `Name.Function`, not `Name.Class`.
- Inheritance `: base_type` after a declaration name → `Name.Class`.
- `import pkg::*;` / `package a::b` → `Name.Namespace`.
- Template parameter lists `<…>` are *not* specially handled; `<` and `>` stay
  `Operator`. Correctly distinguishing template brackets from comparison needs a parser,
  and the cost of getting it wrong (a whole line as one token) exceeds the benefit.

### 6.6 Dialect: standard vs. tool extensions

`pssparser` reserves `pyimport`, `pyobj`, `from`, `init`, `option` — not in the standard.
Highlighting them as keywords in a standards document is wrong; failing to highlight
them in a `pssparser`-flavored file is a minor loss.

**Decided (§12 D1): a `dialect` option, default `"std"`.** `dialect="pssparser"` adds
the extension words plus `numeric` (§3.1). The alias `pss` maps to the default; no
second registered lexer.

### 6.7 Options

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `dialect` | `"std"` \| `"pssparser"` | `"std"` | §6.6 |
| `builtins` | bool | `True` | Core-library names as `Name.Builtin` |
| `target_lexers` | bool | `False` (phase 3 → `True` if lossless) | §6.4 |
| `docstrings` | bool | `True` | `///`, `//!`, `/**`, `/*!` as `Comment.Special` |

All are read in `__init__` via `get_bool_opt`/`get_choice_opt` and affect the token map
built per-instance. Because `RegexLexer.tokens` is a class attribute processed at class
creation, option-dependent rules are handled by making the *token type* a function of
`self` in a callback, not by rebuilding the state machine. Simplest implementation:
one `_builtin_or_name` callback consulted by the identifier rule.

### 6.8 `analyse_text`

Return a moderate confidence (~0.1–0.3) on distinctive multi-word signatures that no
other C-family language has: `\baction\s+\w+\s*\{`, `\bcomponent\s+\w+\s*\{`,
`\bactivity\s*\{`, `\bexec\s+(body|pre_solve|post_solve)\b`, `\bconstraint\s+\w*\s*\{`.
Deliberately conservative: PSS shares too much surface with SystemVerilog to claim high
confidence, and over-claiming steals files from other lexers.

---

## 7. Token type reference (summary)

| Construct | Token |
| --- | --- |
| `// …`, `/* … */` | `Comment.Single`, `Comment.Multiline` |
| `/// …`, `//! …`, `/** … */`, `/*! … */` | `Comment.Special` |
| `compile if/has/assert` | `Comment.Preproc` |
| Keywords | per §6.2 |
| `@ann` | `Name.Decorator` |
| `.field` inside annotation params | `Name.Attribute` |
| Declared name after decl keyword | `Name.Class` / `Name.Function` |
| `pkg::` | `Name.Namespace` |
| `foo(` | `Name.Function` |
| Core-library names | `Name.Builtin` |
| `\escaped+id` | `Name` |
| Other identifiers | `Name` |
| `8'hFF`, `'sd12` | `Number.Hex` / `Number.Bin` / `Number.Oct` / `Number.Integer` by base char |
| `0xFF` / `0b1010` / `0755` / `42` | `Number.Hex` / `Number.Bin` / `Number.Oct` / `Number.Integer` |
| `1.5`, `2e6` | `Number.Float` |
| `"…"` | `String.Double`, escapes `String.Escape` |
| `"""…"""` | `String.Heredoc` |
| `{{expr}}` / `{% … %}` | `String.Interpol` / `Comment.Preproc` + PSS tokens inside |
| Operators, `:=`, `:/`, `->`, `..`, `...` | `Operator` |
| `{}()[];,.` | `Punctuation` |

---

## 8. Testing strategy

### 8.1 Corpus test — no `Token.Error`

The highest value-per-line test available. Lex every file in `tests/corpus/` and assert
zero `Token.Error` and no token longer than N characters (catches runaway states, which
produce *valid* tokens and so slip past the error check).

Corpus sources, all locally available:

- `psstools/example/2/src/pss/` — hand-written PSS
- `zuspec-fe-pss/tests/patterns/` — feature-targeted micro-files
- `peakrdl-pss/tests/golden/expect/` — machine-generated PSS (different style, good
  coverage of register-model idioms)
- `pss-skills/skills/pss-language-ref/examples/`
- Purpose-written 3.1 files exercising annotations, monitors, behavioral coverage,
  triple-quoted strings with mustache/directives, escaped identifiers, and every
  numeric literal form in Clause 4.6.

Corpus files get vendored into this repo (they are small) rather than referenced by
path, so tests run standalone.

### 8.2 Snippet golden tests

Pygments' own `tests/snippets` format: an input file and a checked-in token dump,
regenerable with a `--update-goldens` flag. One snippet per ordering constraint in §6.3
plus one per §6.2 bucket. These are what make a taxonomy change reviewable as a diff.

### 8.3 Entry-point test

Install the package, then assert `get_lexer_by_name("pss")` and
`get_lexer_for_filename("x.pss")` return `PSSLexer`. Guards the packaging metadata,
which no unit test touches.

### 8.4 Vocabulary sync test

§5.

### 8.5 CI matrix

Python 3.9–3.14 (matching the interpreter range `pssparser` builds for) × Pygments
{floor, latest}. The floor leg is the one that catches accidental use of a newer
Pygments API. Being pure Python, this is a plain `actions/setup-python` matrix — none of
`pssparser`'s `manylinux` container machinery is needed.

---

## 9. Migration of `sphinx-pss`

1. Add `pygments-pss` to `sphinx-pss` dependencies.
2. Replace `src/sphinx_pss/lexer.py` with `from pygments_pss import PSSLexer as PssLexer`
   (keeps `sphinx_pss.lexer.PssLexer` importable for anyone who reached in).
3. Keep `app.add_lexer("pss", PssLexer)`.
4. Port `sphinx-pss/tests/test_lexer.py` cases into this repo's snippet tests; leave a
   thin integration test there asserting a `.. code-block:: pss` renders highlighted.
5. Drop `mutable` (not a PSS keyword) and `numeric` (§12 D1), and stop highlighting the
   `pssparser` extensions `pyimport`, `pyobj`, `from`, `init`, `option` unless
   `dialect="pssparser"` is set. These are visible behavior changes relative to the
   current lexer and should be called out in the `sphinx-pss` changelog.

The `sphinx-pss` module docstring already records this hand-off as resolved on
2026-08-13 and says the module should be deleted along with its `app.add_lexer`
registration. Note the discrepancy with §2: **keep** the `app.add_lexer("pss", …)` call
— it is what makes the lexer available when plugin discovery is disabled or the entry
point has not been picked up. Only the lexer *implementation* moves.

---

## 10. Delivery phases

| Phase | Content | Exit criterion |
| --- | --- | --- |
| **1** | Package skeleton, entry point, generator, lexer at parity with `sphinx-pss`'s plus escaped identifiers, full numeric forms, correct annotations, `mutable` removed | Corpus test green; `pygmentize -l pss` works from a clean venv |
| **2** | Triple-quoted string internals (mustache + directives), core-library builtins, declaration-name refinements, `analyse_text` | Snippet goldens for all of §6.3 |
| **3** | Target-language embedding (§6.4), `dialect` option | Decide `target_lexers` default: on only if it shows no regression on corpus (§12 D2) |
| **4** | `sphinx-pss` migration, PyPI publish job (§4.4), README with deviations (§12) | `sphinx-pss` docs build clean under `-W`; wheel installs from PyPI into a clean venv |
| **5** (optional) | Upstream proposal to Pygments | §11 |

---

## 11. Upstreaming considerations

If PSS support is later contributed to Pygments core, the requirements are: the lexer
moves to `pygments/lexers/hdl.py` (or a new `pss.py`), gets registered in the generated
`_mapping.py` via `make mapfiles`, gains a real `version_added`, and ships an example
file under `tests/examplefiles/pss/` with a checked-in golden output plus snippet tests.
Keeping the lexer in one module with no intra-package imports beyond `_keywords`, and
keeping tests in Pygments' snippet format (§8.2), makes that a copy rather than a
rewrite. Upstream's stated position is plugin-first; contribution is a later, optional
step and would leave this package as a thin compatibility shim.

---

## 12. Decisions

Resolved in review, 2026-08-13. The sections above are written to match; this section is
the record of *why*.

- **D1. `numeric` is treated as non-standard.** It is a token in `PSSLexer.g4` and
  occupies the alphabetically correct empty cell in the LRM's damaged Table 3, but
  appears nowhere in Annex B's grammar. Highlighting a non-keyword is a visible error;
  missing one is mild. **Excluded from `dialect="std"`, included in
  `dialect="pssparser"` (§3.1, §6.6).** Revisit against a clean 3.1 PDF when one exists;
  if it turns out to be standard, the change is one line in the generator's mapping.
- **D2. Target-template bodies are not lexed as C/C++/SV by default.** Implemented
  behind `target_lexers`, shipped off through phases 1–2. Phase 3 evaluates it against
  the corpus and flips the default only if it proves lossless (§6.4).
- **D3. Naming stays `pygments-pss` / `pygments_pss`** rather than
  `pygments-accellera-pss` — short and unambiguous within EDA (§4.2).
- **D4. Whitespace-separated based literals (`8'h FF`) are not supported.** The LRM
  permits the form, but supporting it costs a lookahead and risks mis-lexing `8'h`
  followed by an unrelated identifier. Accepted as a known deviation, to be documented
  in the README; revisit if it is reported in real source (§3, §12 note below).
- **D5. Doc-comment highlighting stays**, behind the `docstrings` option, default on.
  `///`, `//!`, `/**`, `/*!` are a psstools convention rather than a PSS one, but they
  cost nothing for projects that do not use them (§6.7).
- **D6. `psstools/pygments-pss`, published the same way as `pssparser`** — self-hosted
  Gitea repo, GitHub-Actions-style CI with a `publish` job using
  `pypa/gh-action-pypi-publish` and the shared `PYPI_API_TOKEN`, `BASE`/`SUFFIX` version
  stamping. Details and the pure-Python simplifications in §4.4.

**Deviations from the LRM, to be listed in the README.** D4 is the only intentional one
so far. D1 is a *conservative* reading rather than a deviation. Anything else the
implementation discovers gets added here rather than left in a code comment.
