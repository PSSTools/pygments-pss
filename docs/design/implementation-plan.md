# `pygments-pss` — Implementation, Test, and Documentation Plan

**Status:** In progress — phases 0–2 complete (378 tests green)
**Companion to:** [`DESIGN.md`](../../DESIGN.md) (reviewed 2026-08-13, decisions D1–D6 accepted)
**Tracking:** every task carries an ID (`P<phase>.<n>`) and a checkbox. Check the box
only when its acceptance criterion is demonstrably met, not when the code is written.
**Progress log:** §9 records what each working session actually landed, including where
reality forced a correction to this plan.

---

## 0. How to read this plan

`DESIGN.md` says *what* the lexer is and *why*. This document says *what to build, in
what order, and how we will know it works*. Where the two disagree, `DESIGN.md` wins and
this file gets corrected.

Three tracks run in parallel across the phases:

| Track | Owner artifact | Where specified |
| --- | --- | --- |
| **Implementation** | `src/pygments_pss/` | §2 |
| **Test** | `tests/` | §3 |
| **Documentation** | `docs/` (Sphinx) + `README.md` | §4 |

Phases are the delivery unit. A phase is *done* when its implementation, its tests, and
its docs are all done — not when the code lands. §5 is the phase-by-phase checklist,
§6 the traceability matrix back to `DESIGN.md`, §7 the risks, §8 the decisions this plan
itself needs.

---

## 1. Project conventions

Settled up front so no task has to relitigate them. Most are inherited from `sphinx-pss`
and `pssparser` so the three repos feel like one stack.

| Concern | Choice | Note |
| --- | --- | --- |
| Build backend | `setuptools>=68` | `DESIGN.md` §4.2 sketched `hatchling`; **`sphinx-pss` uses setuptools and there is no reason to differ.** Settled: §8 P-D1. |
| Layout | `src/` | Tests run against the installed package so the entry point is exercised. |
| Python floor | 3.9 | Widest range `pssparser` builds for. `sphinx-pss` is 3.10+, but this package has no Sphinx dependency. |
| Pygments floor | `>=2.14` | `DESIGN.md` §4.2. |
| Test runner | `pytest>=8` | Markers as in §3.1. |
| Docs | Sphinx + `myst_parser` + `furo` | Matches `sphinx-pss`; Markdown throughout. |
| Formatting | none enforced initially | Add `ruff` only if the diff noise justifies it. |
| Type hints | annotated, `py.typed` shipped, no CI type-check gate in phase 1 | |
| Line width | 88 | Matches `sphinx-pss` sources. |

**Naming reminder:** the class is `PSSLexer`; `PssLexer` exists only as a
backward-compatible alias for `sphinx-pss` (`DESIGN.md` §4.3).

---

## 2. Implementation plan

### 2.0 Phase 0 — Repository bootstrap

Nothing language-specific; gets a green, publishable, empty package so every later phase
has a working feedback loop.

- [x] **P0.1 `pyproject.toml`.** Per `DESIGN.md` §4.2 with the §1 backend correction.
  Dynamic version from `src/pygments_pss/__version__.py`. Declares the
  `[project.entry-points."pygments.lexers"]` mapping from day one, pointing at a stub
  lexer, so P0.6 can assert on it.
  *Accept:* `pip install -e .` succeeds in a clean venv. **Met.** Note: the dynamic
  version uses `attr = "pygments_pss.__version__._pkg_version"`, and setuptools resolves
  it without importing `pygments_pss/__init__.py` — verified explicitly, because that
  `__init__` imports Pygments, which is absent under build isolation.
- [x] **P0.2 `src/pygments_pss/__version__.py`.** `BASE` / `SUFFIX` / `get_version()`,
  copied structurally from `pssparser/python/pssparser/__version__.py` (`DESIGN.md`
  §4.4). `BASE = "0.1.0"`.
  *Accept:* `python -c "import pygments_pss; print(pygments_pss.__version__)"` prints a
  PEP 440 string; in a git tree it carries the `git describe` suffix. **Met** —
  `0.1.0+2ef9ea5`. Deviation from `pssparser`: the `git describe` output is normalised
  to `[0-9A-Za-z.]` before being used as a PEP 440 local version. `pssparser`
  interpolates it raw, which produces a version pip rejects (`v0.1.0-3-gdeadbee`) as
  soon as the repo carries a tag.
- [x] **P0.3 Stub `lexer.py`.** `PSSLexer(RegexLexer)` with metadata per `DESIGN.md`
  §4.3 and a single `(r".", Text)` rule. `__init__.py` re-exports `PSSLexer`,
  `PssLexer`, `__version__`.
  *Accept:* `pygmentize -l pss` on any file emits output rather than an exception. **Met.**
- [x] **P0.4 `ivpm.yaml`.** Add `default-dev` deps: `pytest`, `pygments`, plus a source
  dep on `pssparser` (grammar source for the generator, dev-only — `DESIGN.md` §4.4).
  *Accept:* `ivpm update` in a clean checkout produces `packages/pssparser/src/PSSLexer.g4`.
  **Met.** The `pssparser` dep is declared `type: raw` so it is fetched but not built
  or installed into the venv. It is *not* a shallow clone: with `depth: 1` the
  generator's `git log -1 -- PSSLexer.g4` can only ever report the tip commit, which
  makes the provenance header say something false. Its own `ivpm.yaml` still drags in
  `pyastbuilder`, the ANTLR jar, the ANTLR C++ runtime and gtest — ~17 MB that this
  package has no use for. Tolerated rather than worked around: the alternative is
  vendoring a grammar copy, which is exactly the drift this design is built to avoid.
- [x] **P0.5 CI.** *(Rewritten — see §8 P-D6.)* `.forgejo/workflows/ci.yml`, not
  `.github/`: this repo's remote is the self-hosted Forgejo instance, as `sphinx-pss`'s
  is, and Forgejo resolves bare `uses:` against `code.forgejo.org`, so
  `pypa/gh-action-pypi-publish` and `actions/setup-python` are both unavailable.
  Consequences: the interpreter matrix comes from the `dvkit/pssparser-ci` container's
  `/opt/python` tree (the only reason a pure-Python package uses a container), and the
  publish job uses plain `twine`. The publish job is gated on `refs/tags/v*` rather than
  on push-to-`main`, matching `pssparser`'s Forgejo workflow — which also makes the
  `if: false` placeholder unnecessary, since an untagged push can never reach it.
  It additionally checks that the tag matches `BASE`, and installs the built wheel into
  a clean venv and runs `pygmentize -l pss` before uploading.
  *Accept (revised):* workflow present, tag-gated, and the whole matrix runs as a shell
  loop in one job so `ivpm update` is paid once. **Not yet observed green on the
  runner** — no push has happened yet; re-check at first push.
- [x] **P0.6 `tests/test_entry_point.py`.** §3.5.
  *Accept:* passes against the stub. **Met** — T5.1–T5.7, 7 passed.
- [x] **P0.7 `cspell.json`.** Copy `sphinx-pss/cspell.json` and extend with this repo's
  vocabulary (`pygments`, `pygmentize`, `bygroups`, `tqstring`, `Preproc`, …). Editor
  hygiene only, but the design doc currently produces ~120 spurious warnings.
  *Accept:* no cSpell diagnostics on `DESIGN.md` or this file. **Met** — clean over
  `DESIGN.md`, this plan, `README.md`, `src/`, `tests/`, `pyproject.toml`, `ivpm.yaml`
  and `.forgejo/`.
- [x] **P0.8 `README.md`.** Placeholder: what it is, `pip install pygments-pss`, one
  screenshot-less example. Expanded in P4.3.
- [x] **P0.9 `.gitignore`.** *(Added.)* `packages/`, build outputs, `docs/_build/`.
  Without it the ~60 MB `packages/` tree is a candidate for the first commit.
- [x] **P0.10 Scrub the tailnet host from `DESIGN.md`.** *(Added.)* §4.4 named the
  internal SSH host. This repo is published, and CI fails on exactly that pattern
  (a guard ported from `sphinx-pss`); replaced with `https://git.dvkit.org/...`.

### 2.1 Phase 1 — Correct core lexer

Target: everything `sphinx-pss`'s lexer does, plus the lexical rules it gets wrong or
omits. This is the phase that produces a lexer worth installing.

- [x] **P1.1 `scripts/gen_keywords.py`.** Reads `PSSLexer.g4`, applies the curated
  bucket mapping, emits `src/pygments_pss/_keywords.py` (`DESIGN.md` §5). Behaviors:
  - resolves the grammar from `--grammar`, `$PSS_GRAMMAR`, then `packages/pssparser/src/PSSLexer.g4`;
  - emits a provenance header: grammar git SHA, ~~generation date~~, LRM revision reviewed;
  - **fails loudly** on any grammar keyword absent from the mapping;
  - fails on a mapping entry no longer in the grammar (unless in the explicit
    `EXTRA_KEYWORDS` set holding `pre_body` and `this`);
  - ~~asserts no keyword in one bucket is a strict prefix of a keyword in another~~
    (`DESIGN.md` §6.3 constraint 5).
  *Accept:* regenerating produces a byte-identical `_keywords.py`; deleting a mapping
  entry makes it exit non-zero with the offending word named. **Met**, with three
  corrections:
  - **No generation date.** A timestamp makes byte-identical regeneration impossible,
    which is this task's own acceptance criterion. Provenance is the grammar's
    **sha256** plus the last commit *touching that file* — not repository HEAD, which
    moves on every unrelated `pssparser` commit and would make T7.1 fail spuriously.
  - **Constraint 5 cannot be asserted as written.** "No keyword in one bucket is a
    strict prefix of a keyword in another" is false of PSS itself: `in` prefixes `int`,
    `inout`, `input` and `instance`; `type` prefixes `typedef`; `cover` prefixes
    `coverpoint`. What actually keeps them safe is the trailing `\b` on every keyword
    rule. The generator therefore asserts the *enforceable* invariant — every keyword is
    identifier-shaped, so `\b` delimits it — and the lexer carries a comment saying so.
    §6.3's wording should be corrected in D4.2.
  - **`EXTRA_KEYWORDS` is much larger than "`pre_body` and `this`"**: current
    `PSSLexer.g4` also comments out all nine exec kinds ("make exec-block kinds local
    instead of global keywords") and the four collection types ("treats collection types
    as parameterized classes"), plus `init`. Each carries its reason in the mapping.
- [x] **P1.2 `_keywords.py` (generated).** Buckets exactly as `DESIGN.md` §6.2, plus
  `STD_DIALECT_EXCLUSIONS = ("numeric",)` and `PSSPARSER_KEYWORDS = ("from", "init",
  "numeric", "option", "pyimport", "pyobj")` for D1/§6.6.
  *Accept:* ~~`mutable` absent~~; `annotation`, `pre_body`, `this`, `cover`, `atomic`,
  `symbol`, `monitor`, `replicate`, `yield`, `eventually`, `forall`, `match`, `overlap`
  all present in the right buckets. **Met** apart from `mutable`, where the criterion
  itself is wrong — see the correction below. Also verified: the mapping covers **all
  115 entries** of the LRM's Table 3, with no unclassified word left over.

  > **Correction — `mutable` is a real PSS 3.1 keyword, and stays.** `DESIGN.md` §3.1
  > dispositions it as "absent from Table 3, absent from `PSSLexer.g4` → not a PSS
  > keyword, drop it", and phase 1's headline in §10 is "`mutable` removed". Both are
  > wrong. Clause 9.1.6 *Mutable component attributes* (Mantis8726/8693) defines it,
  > Syntax 27 is its syntax box, and Annex B's `component_data_decl_qualifier`
  > production lists it beside `static const` and `instance`. Current `pssparser`
  > master reserves it (`TOK_MUTABLE`); the sibling checkout `DESIGN.md` was written
  > against predates that commit. Its Table 3 cell is one the PDF conversion destroyed
  > — the same damage §3.1 already cites as the reason `annotation` looks absent.
  > Classified in `MODIFIERS` → `Keyword.Declaration`. `sphinx-pss`'s lexer was right
  > to have it, so this also removes one of the three behaviour changes P4.2 was going
  > to have to write a changelog entry for. `DESIGN.md` §3.1, §10 and §9.5 need the
  > correction in D4.2.
- [x] **P1.3 Comments.** `//`, `/* */` (non-nesting), and the `docstrings`-gated
  `///`, `//!`, `/** */`, `/*! */` → `Comment.Special`. Carried over from `sphinx-pss`
  essentially unchanged; the existing `block`/`docblock` sub-states are correct.
  **Met.** The option is applied by a token *callback* rather than by two rule sets,
  since `RegexLexer.tokens` is built once at class creation (`DESIGN.md` §6.7).
- [x] **P1.4 Numbers — full Clause 4.6.** Replaces the current four rules.
  Ordered: based literal → `0x` → `0b` → float → **octal** → decimal. Token per base
  character, not a bare `Number` (`DESIGN.md` §7).
  - based: `(?:[1-9][0-9_]*)?'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ?_]+`
  - `0[xX][0-9a-fA-F_]+`, `0[bB][01_]+`
  - float: `\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d+)?` **and** `\d[\d_]*[eE][+-]?\d+`
    — the current lexer misses the exponent-only form, so `2e6` lexes as `2` + name.
  - octal: `0[0-7_]*\b` (before decimal)
  - decimal: `[1-9][\d_]*|0`
  *Accept:* snippet test S-NUM covers all eight forms. **Met** — S-NUM plus
  `test_lexical_rules.py`'s constraint 1-3 assertions. One refinement: the based
  literal is four rules, not one, so the token follows the base character
  (`Number.Bin`/`Oct`/`Integer`/`Hex`) as `DESIGN.md` §7 requires.
- [x] **P1.5 Escaped identifiers.** `\\[\x21-\x7E]+` before every operator rule
  (`DESIGN.md` §6.3 constraint 4). Currently absent entirely.
  *Accept:* snippet S-ESCID: `\busa+index`, `\-clock`, `\***error***`, `\net1/\net2`,
  `\{a,b}` each lex as exactly one `Name` token. **Met**, all six LRM examples.
  Consequence worth stating publicly (D4.10): Clause 4.3 terminates an escaped
  identifier at *white space*, so `\net1;` genuinely includes the semicolon. That reads
  as a bug and is not one; `pssparser`'s `ESCAPED_ID` is greedier still.
- [x] **P1.6 Strings.** `"…"` → `String.Double` with `String.Escape` restricted to the
  LRM's table (`\' \" \? \\ \a \b \f \n \r \t \v` and `\[0-7]{3}`), anything else after
  a backslash → `Error`. **Terminate the state at an unescaped newline** so an unclosed
  quote cannot swallow a page.
  *Accept:* snippet S-STR; a file containing a lone `"` produces no token spanning more
  than one line. **Met** — S-STR, `test_unterminated_string_stops_at_the_newline`, and
  `corpus/pathological/unclosed_string.pss` under R2/R4.
- [x] **P1.7 Triple-quoted strings (container only).** `"""…"""` → `String.Heredoc`,
  no escape processing. Internals deferred to P2.1. **Met**, with one addition:
  `pssparser`'s grammar has an `EscapedTripleQuote` fragment, so `\"""` inside the body
  is content rather than a terminator. Without that rule the string ends early and the
  rest of the file lexes as code.
- [x] **P1.8 Annotations.** `@Name` → `Name.Decorator`; the following `{ .field = expr }`
  enters an `annotation-params` state giving `.field` → `Name.Attribute`. The
  `annotation` *declaration* keyword is handled by the P1.9 declaration rule.
  *Accept:* snippet S-ANNOT covers element form, standalone form (`@x {…};`), and
  bare `@x` with no params. **Met.** `annotation-params` nests on an inner `{` so an
  aggregate value cannot close the list early, and `include("root")` handles values, so
  the state cannot strand the rest of the file.
- [x] **P1.9 Keywords and declaration names.** `words()` per bucket in the order of
  `DESIGN.md` §6.3; the "declaration keyword then name" rule with ~~`function` →
  `Name.Function`~~ and everything else → `Name.Class`; `activity` and `exec` excluded.
  **Met**, with two corrections found by the S-KW golden:
  - **`function` and `typedef` are excluded too, not special-cased.** In PSS the name
    comes *after* the type — `function int add(...)`, `typedef bit[3:0] nibble_t` — so
    the "keyword then name" rule highlights the *return type* as the declared name.
    `sphinx-pss`'s lexer has exactly that bug. Nothing is lost: a function name is
    followed by `(` and so already gets `Name.Function` from the call rule. (A
    `typedef`'s name currently stays `Name`; picking it up is a P2.3 candidate.)
  - **The separator is `[ \t]+`, not `\s+`.** With `\s+`, a declaration keyword at the
    end of a line claims the first identifier of the *next* line as a declared name.
    The same bug existed in the `compile if|has|assert` rule, where `\s+` paired a
    trailing `compile` with an unrelated `has` on the following line. Both found by
    writing S-KW as one keyword per line; both now have regression tests.
- [x] **P1.10 Identifiers, namespaces, operators, punctuation.** `ident::` →
  `Name.Namespace`; `ident(` → `Name.Function`; the full operator set from
  `DESIGN.md` §3 including `->`, `:=`, `:/`, `...`, `..`, `**`.
  *Accept:* snippet S-OPS; `a..b` is one `..` not two `.`; `:/` and `:=` are single
  tokens inside a `dist` block. **Met.** The operator rule is an explicit
  longest-first alternation rather than `sphinx-pss`'s `[-+*/%!~^&|<>=?:]+`, which
  merged `a =- b` into a single operator token.
- [x] **P1.11 `docstrings` option.** `get_bool_opt`, default `True`; when off, doc
  comment forms fall through to ordinary comment tokens. **Met** — T6.4, plus the
  `s-comment` / `s-comment-nodoc` golden pair, which diffs to exactly what the option
  does.

### 2.2 Phase 2 — Richness

- [x] **P2.1 Triple-quoted string internals.** `{{ … }}` → `String.Interpol`
  delimiters with PSS-lexed contents; `{% … %}` → `Comment.Preproc` delimiters with
  PSS-lexed contents; `{%%}` close directive. Requires an `expr` state reachable via
  `using(this, state=…)`.
  *Accept:* snippet S-TQ; a `{{` with no closing `}}` does not run to end of file.
  **Met.** The `expr` state is a *reduced* PSS expression grammar, not
  `using(this, state=…)` over `root`: root's string rules could re-enter `tqstring`
  from inside a template element, and a declaration inside a mustache expression is not
  a thing. Both `tqexpr` and `tqdirective` carry a zero-width `(?=""")` guard that pops
  silently, so an unclosed `{{` recovers at the string terminator and the code after it
  still lexes as code — asserted, not assumed.
- [x] **P2.2 Core-library builtins.** `_builtins.py` (hand-curated from LRM Annex C,
  not generated — the annex is prose-embedded code, not a machine-readable list) listing
  `std_pkg` / `executor_pkg` / `addr_reg_pkg` / `sync_pkg` names. Identifier rule
  consults a `_builtin_or_name` callback (`DESIGN.md` §6.7).
  *Accept:* `std_pkg::print(...)` gives `Name.Builtin` for both `std_pkg` and `print`;
  a user function named `print` also matches — accepted false positive, documented.
  **Met.** Curated mechanically from Annex C and then filtered by hand against
  `corpus/stdlib/`, which vendors a working implementation of the same four packages.
  Two categories were curated and then **deliberately dropped**, because they would
  mis-highlight user code more often than they would help:
  - **Enum members** (`LOW`, `HIGH`, `NONE`, `FULL`, `READ`, `RANDOM`, `SHARED`, `SKIP`,
    `C`). PSS capitalises enum members by convention, so these are exactly the names a
    user's own enum uses. The types that contain them are matched, which is where the
    reader gets the signal.
  - **`sync_pkg`'s `channel_c` methods** `get`, `put`, `try_get`, `try_put`, `read`,
    `write`. `print` is kept despite the same risk, because `DESIGN.md` §6.7 names it as
    the case that justifies the feature at all.
- [x] **P2.3 Declaration-name refinements.** Inheritance `: base` → `Name.Class`;
  `import a::b::*;` and `package a::b` → `Name.Namespace`.
  **Met**, via two small states rather than more root rules. Two things the task did not
  anticipate:
  - **`import` is not always followed by a package path.** `import solve function
    ext_pkg::alloc_addr;` is legal (LRM §19432, `import_function`), so the rule carries
    a negative lookahead for "the next word is a keyword". Without it, `solve` becomes a
    namespace.
  - **A templated declaration loses its base type.** `struct s<type T> : base_s` — the
    `declaration-suffix` state pops at `<`, since `DESIGN.md` §6.5 rules out treating
    template brackets specially. Known and accepted; recorded in D4.10.
  - A `typedef`'s declared name is still `Name` (see P1.9). Left as-is: picking it up
    means matching backwards past an arbitrary type expression.
- [x] **P2.4 `analyse_text`.** `DESIGN.md` §6.8, capped at 0.3.
  *Accept:* test asserts PSS beats `guess_lexer` alternatives on three corpus files and
  that a plain C file does **not** select `PSSLexer`. **Met**, with one signature
  dropped and two added.
  > **`constraint \w*\s*\{` is not a signature.** `DESIGN.md` §6.8 lists it. But
  > SystemVerilog classes have constraint blocks with identical syntax, and
  > `SystemVerilogLexer` **has no `analyse_text` of its own** — it scores 0.0 on its own
  > source. So any non-zero weight lets PSS win a SystemVerilog file outright, which is
  > precisely the over-claiming §6.8 sets out to avoid. Dropped; `monitor <name> {` and
  > `do <action>;` added in its place, both of which no other C-family language has. A
  > test pins the SystemVerilog premise, so if upstream ever adds an `analyse_text` the
  > reasoning gets re-examined rather than silently rotting.
- [x] **P2.5 `builtins` option.** Default `True`. **Met** — T6.3, the
  `s-builtin` / `s-builtin-off` golden pair, and the R1–R3 sweep now runs the full
  `docstrings` × `builtins` cross-product.

### 2.3 Phase 3 — Options and embedding

- [ ] **P3.1 `dialect` option.** `get_choice_opt`, `"std"` (default) | `"pssparser"`.
  `"pssparser"` adds `PSSPARSER_KEYWORDS`; `"std"` excludes them and `numeric` (D1).
- [ ] **P3.2 Target-language embedding.** Capture `language_identifier` in
  `exec <kind> <lang> = """…""";` and delegate the body to `CLexer` / `CppLexer` /
  `SystemVerilogLexer`. Imports must stay **lazy** (inside the callback) so the default
  path does not pay for them.
- [ ] **P3.3 Evaluate and decide `target_lexers` default (D2).** Run the corpus with the
  option on and off; diff token streams. Flip the default to `True` only if no
  regression. Record the outcome in `DESIGN.md` §12 D2 either way.
  *Accept:* a written result in the decision record, not just a code change.

### 2.4 Phase 4 — Release and migration

- [ ] **P4.1 Enable the publish job.** Remove the `if: false` from P0.5; tag `v0.1.0`.
  *Accept:* `pip install pygments-pss` into a clean venv, then
  `pygmentize -l pss file.pss` — from PyPI, not the working tree.
- [ ] **P4.2 Migrate `sphinx-pss`** per `DESIGN.md` §9, including the changelog entries
  for the `mutable` / `numeric` / `pssparser`-extension behavior changes, and resolving
  the `app.add_lexer` discrepancy flagged there.
  *Accept:* `sphinx-pss` docs build clean under `-W` with its own `lexer.py` reduced to
  a re-export.
- [ ] **P4.3 README.** Install, usage in Sphinx/MkDocs/`pygmentize`, options table,
  deviations list (§12 D4), link to the docs site.

### 2.5 Phase 5 — Optional upstreaming

- [ ] **P5.1** Per `DESIGN.md` §11. Not scheduled.

---

## 3. Test plan

### 3.1 Structure and markers

```
tests/
├── conftest.py                 fixtures: lexer instances per option combination
├── corpus/                     vendored .pss (§3.2)
├── snippets/                   <name>.pss + <name>.tokens (§3.3)
├── test_no_error_tokens.py     corpus sweep
├── test_snippets.py            golden comparison
├── test_lexical_rules.py       targeted unit assertions (§3.4)
├── test_entry_point.py         packaging (§3.5)
├── test_options.py             option matrix
├── test_vocabulary_sync.py     generator drift guard
└── test_analyse_text.py
```

Landed in phase 1: `conftest.py`, `corpus/`, `snippets/`, `test_no_error_tokens.py`,
`test_snippets.py`, `test_lexical_rules.py`, `test_entry_point.py`, `test_options.py`,
`test_vocabulary_sync.py`. `test_analyse_text.py` arrives with P2.4.

Markers, mirroring `sphinx-pss`'s conventions:

| Marker | Meaning |
| --- | --- |
| `unit` | pure token-stream assertions |
| `corpus` | sweeps over `tests/corpus/`; **not** opt-in here (unlike `sphinx-pss`) — it is fast and is the primary signal |
| `upstream` | asserts a `pssparser` grammar fact this package depends on; a failure is a failure, never a skip |

### 3.2 Corpus (`tests/corpus/`)

Vendored, not path-referenced, so the suite runs standalone (`DESIGN.md` §8.1).

- [x] **T2.1** Vendor from `psstools/example/2/src/pss/` — hand-written idiomatic PSS.
- [x] **T2.2** ~~Vendor from `zuspec-fe-pss/tests/patterns/`~~ — that directory no longer
  exists in `zuspec-fe-pss`. Vendored `src/stdlib/` instead: `std_pkg`, `executor_pkg`,
  `addr_reg_pkg`, `sync_pkg`, `packed_s` — the PSS core library's own source. A better
  substitute than what it replaces, since it is exactly the vocabulary P2.2 has to
  recognise.
- [x] **T2.3** Vendor from `peakrdl-pss/tests/golden/expect/` — machine-generated,
  register-model idioms.
- [x] **T2.4** Vendor from `pss-skills/skills/pss-language-ref/examples/`.
- [x] **T2.5** Author `corpus/pss31/` covering 3.1-only surface: annotations
  (declaration, element, standalone), `monitor`, behavioral coverage (`cover` with
  `sequence`/`eventually`/`overlap`), triple-quoted strings with mustache and
  control-flow directives, `replicate`, `symbol`, `yield`.
- [x] **T2.6** Author `corpus/lexical/` — one file per Clause 4 subsection: every
  numeric form, every escape sequence, escaped identifiers, comment forms, operator
  soup. These exist to be *lexically* nasty, not semantically meaningful.
- [x] **T2.7** Author `corpus/pathological/` — deliberately broken input: unclosed
  string, unclosed comment, unclosed `{{`, a lone `\`, a lone `'`, a truncated file
  mid-token. Asserted separately (§3.3 R4): must not hang, must not produce a token
  spanning the rest of the file.

Each vendored directory gets a `PROVENANCE.md` naming the source repo and commit.

### 3.3 Rule assertions over the corpus (`test_no_error_tokens.py`)

- [x] **T3.1 R1 — no `Token.Error`** in any file under `corpus/` except
  `corpus/pathological/`.
- [x] **T3.2 R2 — no oversized token.** No single token longer than 200 characters
  outside comments and triple-quoted strings. Catches runaway states, which produce
  *valid* tokens and slip past R1. This is the highest-yield assertion in the suite.
- [x] **T3.3 R3 — round-trip fidelity.** `"".join(value for _, value in tokens)` equals
  the input exactly, for every corpus file. Pygments guarantees it; a bad
  `bygroups`/callback breaks it, and nothing else in the suite would notice.
- [x] **T3.4 R4 — pathological input terminates.** Each `corpus/pathological/` file
  lexes within a time bound and satisfies R2 and R3.
- [x] **T3.5 R5 — option independence.** R1–R3 hold for every combination in the
  §3.6 option matrix, not just defaults.

### 3.4 Snippet goldens (`tests/snippets/`)

Pygments' own format: input file plus a checked-in token dump, regenerated with
`pytest --update-goldens`. Two meta-tests guard the guard: a snippet with no golden
would pass vacuously, and a golden whose input was deleted still reads as coverage. One per ordering constraint in `DESIGN.md` §6.3, one per
keyword bucket in §6.2, one per construct in §7.

- [x] **T4.1 S-NUM** — `4'sd12`, `'hFF`, `8'b1010_1010`, `0xDEAD_BEEF`, `0b1101`,
  `0755`, `42`, `20.14`, `2e6`, `1e-9`. Guards constraints 1–3.
- [x] **T4.2 S-ESCID** — the five LRM examples. Guards constraint 4.
- [x] **T4.3 S-KW** — one line per §6.2 bucket. Guards constraint 5 and makes any
  taxonomy change show up as a reviewable diff.
- [x] **T4.4 S-COMMENT** — all six comment forms. Guards constraint 6.
- [x] **T4.5 S-STR** — quoted string with each legal escape, an illegal escape, an
  unterminated string. Guards constraint 7.
- [x] **T4.6 S-TQ** — triple-quoted string with mustache, `{% if %}`/`{%%}`, embedded
  single and double quotes, embedded newlines. *(P2.1)*
- [x] **T4.7 S-ANNOT** — declaration, element application, standalone, no-params.
- [x] **T4.8 S-DECL** — `action`/`component`/`struct`/`function`/`package` with names,
  inheritance, `extend`, and the excluded `exec body` / `activity {` forms.
- [x] **T4.9 S-OPS** — full operator set including `->`, `:=`, `:/`, `..`, `...`, `**`,
  and a `dist` block.
- [x] **T4.10 S-EXEC** — every `exec_kind`, plus target-code and target-file forms.
- [x] **T4.11 S-BUILTIN** — `std_pkg::print`, `urandom_range`, `addr_claim_s`, and a
  user-defined identifier that shadows a builtin name. *(P2.2)*
- [ ] **T4.12 S-TARGET** — `exec body C = """…"""` with `target_lexers` both on and
  off, two goldens. *(P3.2)*

### 3.5 Packaging (`test_entry_point.py`)

- [x] **T5.1** `get_lexer_by_name("pss")` returns `PSSLexer`.
- [x] **T5.2** `get_lexer_by_name("portable-stimulus")` returns `PSSLexer`.
- [x] **T5.3** `get_lexer_for_filename("x.pss")` returns `PSSLexer`.
- [x] **T5.4** `get_lexer_for_mimetype("text/x-pss")` returns `PSSLexer`.
- [x] **T5.5** `PssLexer is PSSLexer` (the `sphinx-pss` compatibility alias).
- [x] **T5.6** The distribution advertises exactly one `pygments.lexers` entry point.
- [x] **T5.7** `pygmentize -l pss` on a corpus file exits 0 — a subprocess test, since
  it is the only one that exercises the real installed-console path.

### 3.6 Options (`test_options.py`) and CI matrix

Option matrix asserted: `dialect` × `builtins` × `docstrings` × `target_lexers`
(2×2×2×2). Full cross-product only in the R1–R3 sweep (T3.5); targeted assertions
otherwise:

- [ ] **T6.1** `dialect="std"`: `pyimport`, `numeric` → `Name`.
- [ ] **T6.2** `dialect="pssparser"`: same words → `Keyword`.
- [x] **T6.3** `builtins=False`: `urandom` → `Name`.
- [x] **T6.4** `docstrings=False`: `/// x` → `Comment.Single`.
- [x] **T6.5** Unknown option value raises, rather than silently defaulting.

CI matrix: Python 3.9–3.14 × Pygments {2.14, latest}. Plain `actions/setup-python` —
no manylinux container (`DESIGN.md` §4.4, §8.5).

### 3.7 Drift guards

- [x] **T7.1 `test_vocabulary_sync.py`** — re-run the generator in memory; assert the
  checked-in `_keywords.py` matches. Marked `upstream`: a `pssparser` keyword addition
  must fail CI, not skip.
- [x] **T7.2** Assert the grammar file the generator read is the one recorded in
  `_keywords.py`'s provenance header, so a stale `packages/` checkout is caught.
- [x] **T7.3** Assert every keyword in `_keywords.py` appears in exactly one bucket.

---

## 4. Documentation plan (`docs/`)

Sphinx + `myst_parser` + `furo`, mirroring `sphinx-pss`. The docs **dogfood the lexer**:
every PSS block on the site is highlighted by the package being documented, so
`sphinx-build -W` is a real regression signal, exactly as `sphinx-pss`'s conf.py notes
for its own extension.

### 4.1 Tree

```
docs/
├── conf.py
├── index.md
├── getting-started.md
├── usage/
│   ├── options.md
│   ├── sphinx.md
│   ├── mkdocs.md
│   └── cli.md
├── reference/
│   ├── token-map.md
│   └── deviations.md
├── design/
│   ├── index.md
│   ├── implementation-plan.md      (this file)
│   └── pygments-pss-design.md      (DESIGN.md moves here in D4.2)
└── _static/
```

### 4.2 Tasks

- [ ] **D4.1 `conf.py`.** `myst_parser`, `furo`, `nitpicky = False`,
  intersphinx to Sphinx and Pygments. **No `sphinx_pss` extension** — that would make
  the dependency circular (`sphinx-pss` depends on this package). Highlighting comes
  from the entry point alone, which is the point.
- [ ] **D4.2 Move `DESIGN.md`** to `docs/design/pygments-pss-design.md` and leave a
  one-line stub at the repo root pointing at it, matching `sphinx-pss`'s layout. Fix
  this file's relative link when that happens.
- [ ] **D4.3 `index.md`.** What it is, the one-paragraph pitch, install line, a
  highlighted PSS sample as the first thing a visitor sees, toctrees.
- [ ] **D4.4 `getting-started.md`.** `pip install pygments-pss`; verify with
  `pygmentize -l pss`; the "it just works after install, no configuration" point stated
  explicitly, because that is the entry-point payoff and users will not assume it.
- [ ] **D4.5 `usage/options.md`.** The four options: meaning, default, worked
  before/after example for each. Sourced from the same table as §6.7 of the design so
  they cannot drift — a doc test asserts the option names listed here match
  `PSSLexer`'s accepted options.
- [ ] **D4.6 `usage/sphinx.md`.** `.. code-block:: pss` and MyST ` ```pss `; the
  `highlight_language` setting; passing options via `highlight_options`; the note that
  `sphinx-pss` users get this transitively.
- [ ] **D4.7 `usage/mkdocs.md`.** Fenced blocks, `pymdownx.highlight` config, and the
  fact that no `mkdocs.yml` entry is needed beyond installing the package.
- [ ] **D4.8 `usage/cli.md`.** `pygmentize` recipes: HTML fragment, standalone HTML with
  `-O full`, terminal 256-colour, LaTeX. Includes generating the CSS with `-S`.
- [ ] **D4.9 `reference/token-map.md`.** The construct → token table (`DESIGN.md` §7),
  presented for someone writing a custom style: what to colour to make PSS read well.
  Rendered alongside a live highlighted sample.
- [ ] **D4.10 `reference/deviations.md`.** Known departures from the LRM and known
  false positives — D4's `8'h FF`, the builtin-shadowing false positive from P2.2, the
  unhandled template-bracket case from §6.5, and the `numeric` question (D1) with its
  revisit condition. **This page is the honesty budget; keep it current.**
- [ ] **D4.11 `design/index.md`.** Toctree over the design doc and this plan.
- [ ] **D4.12 Docs build in CI.** `sphinx-build -W -b html docs docs/_build/html` as a
  required job, plus `-b linkcheck` non-blocking.
- [ ] **D4.13 `tests/test_docs_build.py`.** Asserts the built HTML for a `pss` code
  block actually contains highlight spans — catches a docs build that silently falls
  back to plain text, which `-W` alone does not.
- [ ] **D4.14 Publish.** GitHub Pages via `peaceiris/actions-gh-pages`, as `pssparser`
  does, on push to `main`.

### 4.3 Docstrings

Module and class docstrings carry the *why* (which LRM clause a rule implements),
following the style already used in `sphinx-pss/src/sphinx_pss/lexer.py`. Every regex
whose ordering is load-bearing gets a comment naming the `DESIGN.md` §6.3 constraint it
satisfies, so a well-meaning reorder is caught in review rather than by a golden diff.

---

## 5. Phase checklist

| Phase | Implementation | Tests | Docs | Exit criterion |
| --- | --- | --- | --- | --- |
| **0** ✅ | P0.1–P0.10 | T5.1–T5.7 | *(deferred)* | `pip install -e .` + `pygmentize -l pss` work |
| **1** ✅ | P1.1–P1.11 | T2.1–T2.7, T3.1–T3.5, T4.1–T4.5, T4.7–T4.10, T6.4, T6.5, T7.1–T7.3 | *(deferred to phase 2)* | Corpus sweep green; goldens for §6.3 constraints 1–7 |
| **2** ✅ | P2.1–P2.5 | T4.6, T4.11, T6.3, `test_analyse_text.py` | *(deferred to phase 3)* | 3.1 corpus files clean; `analyse_text` does not steal C files |
| **3** | P3.1–P3.3 | T4.12, T6.1–T6.5 | D4.5 (complete) | D2 decision recorded with corpus evidence |
| **4** | P4.1–P4.3 | full suite on the PyPI artifact | D4.6–D4.8, D4.11–D4.14 | `sphinx-pss` builds `-W` clean against the released wheel |
| **5** | P5.1 | — | — | not scheduled |

---

## 6. Traceability

| `DESIGN.md` | Tasks |
| --- | --- |
| §3 Clause 4.1 comments | P1.3, T4.4 |
| §3 Clause 4.3 escaped identifiers | P1.5, T4.2 |
| §3 Clause 4.6 numbers | P1.4, T4.1 |
| §3 Clause 4.7 strings | P1.6, P1.7, P2.1, T4.5, T4.6 |
| §3 Annex B.5 exec | P1.9, P3.2, T4.10, T4.12 |
| §3 Annex B.6 annotations | P1.8, T4.7 |
| §3 Annex C core library | P2.2, T4.11 |
| §3.1 keyword-table defects | P1.1, P1.2, T7.1–T7.3 |
| §4.1–§4.3 packaging | P0.1–P0.3, T5.1–T5.7 |
| §4.4 publishing | P0.5, P4.1 |
| §5 drift control | P1.1, T7.1, T7.2 |
| §6.2 taxonomy | P1.2, P1.9, T4.3 |
| §6.3 ordering constraints | P1.3–P1.10, T4.1–T4.5 |
| §6.4 target templates | P2.1, P3.2, P3.3, T4.12 |
| §6.5 declaration names | P1.9, P2.3, T4.8 |
| §6.6 dialect | P3.1, T6.1, T6.2 |
| §6.7 options | P1.11, P2.5, P3.1, T6.1–T6.5, D4.5 |
| §6.8 `analyse_text` | P2.4 |
| §7 token map | T4.* , D4.9 |
| §8 testing | all T* |
| §9 `sphinx-pss` migration | P4.2 |
| §12 D1 `numeric` | P1.2, P3.1, T6.1, D4.10 |
| §12 D2 target lexers | P3.3, T4.12 |
| §12 D4 `8'h FF` | D4.10 |
| §12 D5 doc comments | P1.11, T6.4 |
| §12 D6 publishing | P0.5, P4.1 |

---

## 7. Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| R-1 | **Runaway states in a docs build.** An unclosed string or `{{` swallowing a page is the worst realistic failure — it is silent and it is visible to end users. | T3.2 (oversized token) + T3.4 (pathological corpus). Explicit newline termination in P1.6. |
| R-2 | **Corpus is unrepresentative.** All four vendored sources are from this stack; other vendors' PSS may use constructs none of them exercise. | T2.5/T2.6 authored specifically from the LRM rather than from existing code. Re-examine after any external bug report. |
| R-3 | **`numeric` decision is wrong** (D1). | Isolated to one line in the generator mapping; T6.1/T6.2 pin both behaviors; D4.10 states the uncertainty publicly. |
| R-4 | **Generator coupling to `pssparser`.** A grammar refactor could break parsing of `PSSLexer.g4`. | Generator failure is loud (P1.1) and dev-only — `_keywords.py` is checked in, so a released wheel is unaffected. |
| R-5 | **Golden-test churn.** A taxonomy tweak rewrites many `.tokens` files, making review noisy. | Keep snippets small and single-purpose; `--update-goldens` diff is the review artifact. |
| R-6 | **Circular dev dependency** between `sphinx-pss` and this package's docs. | D4.1: this site does **not** use the `sphinx_pss` extension. |
| R-7 | **Phase-3 embedding proves lossy** and the default stays off, making the work look wasted. | Accepted: the option still serves users who want it, and the corpus evidence is the deliverable (P3.3). |

---

## 8. Decisions this plan needs

All resolved as recommended unless noted. Each was a documented recommendation with no
counter-argument found while implementing; they are recorded here as settled rather than
re-opened.

- [x] **P-D1. Build backend → `setuptools`.** `DESIGN.md` §4.2 sketched `hatchling`; §1
  here proposes `setuptools` to match `sphinx-pss`. **Resolved: setuptools.** `DESIGN.md`
  §4.2's TOML sketch is now stale on this one point; corrected in D4.2 when the design
  doc moves rather than by editing a reviewed document in place.
- [ ] **P-D2. Does `DESIGN.md` move into `docs/design/`** (D4.2), matching `sphinx-pss`,
  or stay at the repo root? *Recommendation: move, with a root stub.* **Still open** —
  deferred to D4.2 in phase 1's documentation slice, since moving it now would break the
  relative link from this file for no gain.
- [x] **P-D3. Corpus vendoring vs. `ivpm` source deps → vendor.** Per `DESIGN.md` §8.1:
  the corpus is a frozen test input, and a corpus that changes under you is worse than
  one that ages. Each vendored directory carries a `PROVENANCE.md`.
- [x] **P-D4. Python floor → 3.9.** Matches `pssparser`'s build range; this package has
  no Sphinx dependency and nothing in it needs 3.10 syntax.
- [x] **P-D5. A bare `0` is `Number.Integer`, not `Number.Oct`.** The LRM's grammar makes
  it an `oct_number`, but nobody reads `0` as octal and `Number.Oct` on it looks like a
  bug. `00`, `0755` and so on remain `Number.Oct`. Documented in `reference/deviations.md`
  (D4.10).
- [x] **P-D6. CI platform → Forgejo Actions, tag-gated publish.** *(New; discovered
  while implementing P0.5.)* This plan and `DESIGN.md` §4.4 both describe GitHub Actions
  with `pypa/gh-action-pypi-publish` gated on push-to-`main`. That is not what the stack
  runs: this repo's only remote is the self-hosted Forgejo instance, `sphinx-pss` has
  `.forgejo/workflows/ci.yml` and no `.github/`, and `pssparser`'s Forgejo workflow
  publishes with plain `twine` gated on `refs/tags/v*`. Resolved to match the stack.
  Rationale for the tag gate specifically, quoting `pssparser`: a version number on PyPI
  "can be yanked but never reused", so ordinary pushes must not be able to reach it.
  `DESIGN.md` §4.4 and D6 are stale on this point and should be corrected in D4.2.

---

## 9. Progress log

### 2026-08-13 — phase 0

Landed P0.1–P0.10. The package installs, the entry point resolves, `pygmentize -l pss`
works, and `tests/test_entry_point.py` (T5.1–T5.7) passes against the stub lexer.

Three things the plan did not anticipate:

1. **CI is Forgejo, not GitHub** (P-D6). The plan's P0.5 was written against
   `DESIGN.md` §4.4, which describes a GitHub workflow this stack does not use.
2. **`DESIGN.md` leaked the internal tailnet host** in §4.4. CI's
   internal-identifier guard — ported from `sphinx-pss`, and worth keeping — would have
   failed on the first push. Fixed (P0.10).
3. **The `ivpm` venv ships no `pip`**, so `python -m ensurepip` is a required step
   before an editable install in a fresh checkout. Worth knowing before debugging it
   again; not worth a plan task.

### 2026-08-13 — phase 1

Landed P1.1–P1.11 and the phase-1 test slice: 359 tests green, including R1 (no
`Token.Error`) over **85 vendored corpus files** and 11 snippet goldens.

The corrections are recorded against their tasks above. The three that change what
someone reading `DESIGN.md` would believe:

1. **`mutable` is a PSS 3.1 keyword** (P1.2). `DESIGN.md` §3.1 says to drop it; the LRM
   defines it in clause 9.1.6 and Annex B, and current `pssparser` reserves it.
2. **§6.3 constraint 5 is not true as written** (P1.1). `in` prefixes `int`; the
   trailing `\b` is what makes that safe, not an absence of prefixes.
3. **The "declaration keyword then name" rule must not span a line break** (P1.9), and
   neither must `compile if`. Both were found by writing the S-KW golden one keyword per
   line, which is the argument for that golden's format.

Also worth knowing: `Lexer.get_tokens` strips leading/trailing newlines (`stripnl`) and
appends one (`ensurenl`) before the rules see the text, so an exact round-trip assertion
(R3) has to go through `get_tokens_unprocessed`. The first draft of R3 failed on four
corpus files for that reason and not for any lexer defect.

**Not done in phase 1, deliberately:** the documentation slice (D4.2, D4.4, D4.9). It is
folded into phase 2 rather than dropped — `DESIGN.md` needs the corrections above before
it moves to `docs/design/`, and writing the token-map page against a lexer that is about
to gain builtins and target templates would mean writing it twice.

### 2026-08-13 — phase 2

Landed P2.1–P2.5: 378 tests green. Template internals, core-library builtins, package/
import and inheritance names, and `analyse_text`.

Two decisions where the plan said "add it" and the right answer was "add less than
that", both recorded against their tasks above:

1. **`constraint` is not an `analyse_text` signature** (P2.4). `SystemVerilogLexer`
   scores 0.0 on its own source, so a shared signature at *any* weight takes SV files.
2. **Core-library enum members are not highlighted** (P2.2). `LOW`, `HIGH`, `READ`, `C`
   are what a user's own enum is called.

The documentation track (D4.2, D4.4, D4.5, D4.9, D4.10) is now the whole of what phases
1 and 2 still owe. It moves to phase 3, where `DESIGN.md`'s corrections — `mutable`,
§6.3 constraint 5, §6.8, and the §4.4/D6 CI description — are applied as part of the
D4.2 move rather than as scattered edits to a reviewed document.
