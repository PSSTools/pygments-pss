# pygments-pss

A [Pygments](https://pygments.org) lexer for the Accellera **Portable Test and Stimulus
Standard** (PSS), packaged as a plugin. Installing it is the entire configuration step:

```bash
pip install pygments-pss
```

After that, `pss` is a language Pygments knows about everywhere it looks — no
`conf.py` entry, no `mkdocs.yml` entry, no registration call:

```bash
pygmentize -l pss my_test.pss
```

````markdown
```pss
component pss_top {
    action entry {
        activity {
            do mem_write;
        }
    }
}
```
````

Targets **PSS 3.1** (Draft 19), including annotations, monitors, behavioral coverage and
triple-quoted target templates, and lexes earlier revisions unchanged.

## Why

Pygments ships no PSS lexer, so every documentation pipeline that shows PSS either
renders it as plain text or hand-rolls a lexer. This is that lexer, once, with tests.

## Usage

**Sphinx** — nothing to configure; the entry point is enough.

```rst
.. code-block:: pss

   component pss_top { }
```

MyST/Markdown fences (```` ```pss ````) work the same way. Options go through
`highlight_options`:

```python
highlight_options = {"pss": {"builtins": False}}
```

**MkDocs** — install the package; `pymdownx.highlight` picks it up. No `mkdocs.yml`
change is needed beyond whatever highlighting extension you already use.

**Command line**

```bash
pygmentize -l pss -f html -O full,style=friendly -o out.html my_test.pss
pygmentize -S friendly -f html > pygments.css     # stylesheet for fragments
pygmentize -l pss -f terminal256 my_test.pss      # 256-colour terminal
```

**Python**

```python
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

print(highlight(source, get_lexer_by_name("pss"), HtmlFormatter()))
```

## Options

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `docstrings` | bool | `True` | Highlight `///`, `//!`, `/** */` and `/*! */` as `Comment.Special`. A psstools convention rather than a PSS one; costs nothing for projects that do not use it. |
| `builtins` | bool | `True` | Highlight core-library names (Annex C: `std_pkg`, `executor_pkg`, `addr_reg_pkg`, `sync_pkg`) as `Name.Builtin`. |

Two further options — `dialect` (standard versus `pssparser` extensions) and
`target_lexers` (lex a `exec body C = """…"""` body as C/C++/SystemVerilog) — are
designed but **not implemented in this release**.

## What gets highlighted

| Construct | Token |
| --- | --- |
| `// …`, `/* … */` | `Comment.Single`, `Comment.Multiline` |
| `/// …`, `//! …`, `/** … */` | `Comment.Special` |
| `compile if` / `has` / `assert` | `Comment.Preproc` |
| Type-declaring and qualifier keywords | `Keyword.Declaration` |
| Built-in types | `Keyword.Type` |
| `true`, `false`, `null` | `Keyword.Constant` |
| `this`, `super` | `Name.Builtin.Pseudo` |
| `@ann`, `.field` in its parameters | `Name.Decorator`, `Name.Attribute` |
| Declared name after a declaration keyword, and its base type | `Name.Class` |
| `package a::b`, `import a::b::*` | `Name.Namespace` |
| `foo(` | `Name.Function` |
| Core-library names | `Name.Builtin` |
| `8'hFF`, `0xFF`, `0b1010`, `0755`, `42` | `Number.Hex` / `Bin` / `Oct` / `Integer`, by base |
| `1.5`, `2e6` | `Number.Float` |
| `"…"` / `"""…"""` | `String.Double` / `String.Heredoc` |
| `{{expr}}` / `{% … %}` in a template | `String.Interpol` / `Comment.Preproc`, with PSS tokens inside |

## Known deviations and false positives

Kept short and honest rather than absent:

- **Whitespace-separated based literals are not supported.** The LRM permits `8'h FF`;
  supporting it costs a lookahead and risks mis-lexing `8'h` followed by an unrelated
  identifier. `8'hFF` is the supported form.
- **An escaped identifier runs to whitespace, so `\net1;` includes the semicolon.**
  That is Clause 4.3's rule, not a defect — the terminator is white space and nothing
  else. Write `\net1 ;` if you want the semicolon back.
- **A user-defined name that shadows a core-library name is highlighted as a builtin.**
  A `RegexLexer` has no scope information. Turn it off with `builtins=False`.
- **`numeric` is not treated as a keyword.** It appears in `pssparser`'s token list and
  in a damaged cell of the LRM's keyword table, but nowhere in the Annex B grammar.
  Highlighting a non-keyword is a visible error; missing one is mild.
- **Tool extensions are not keywords**: `pyimport`, `pyobj`, `from`, `init`, `option`
  are `pssparser` reservations, not PSS.
- **Template parameter brackets are not special.** `<` and `>` stay `Operator`;
  distinguishing them from comparison needs a parser. One consequence: a templated
  declaration's base type (`struct s<type T> : base_s`) is not highlighted as a class.
- **A `typedef`'s declared name** is an ordinary `Name`, because in `typedef bit[3:0]
  nibble_t;` the name comes after an arbitrary type expression.

## Requirements

Python 3.9+ and Pygments 2.14+. No other runtime dependency: no parser, no ANTLR,
no compiler.

## License

Apache-2.0. See [LICENSE](LICENSE).
