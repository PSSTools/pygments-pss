# pygments-pss

A [Pygments](https://pygments.org) lexer for the Accellera **Portable Test and Stimulus
Standard** (PSS), packaged as a plugin. Installing it is the entire configuration step:

```bash
pip install pygments-pss
```

After that, `pss` is a language Pygments knows about everywhere it looks — the CLI,
Sphinx, MkDocs, and anything else built on Pygments:

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

Targets PSS 3.1, including annotations, monitors, behavioral coverage and
triple-quoted target templates, and lexes earlier revisions unchanged.

Full documentation, the option reference and the list of known deviations from the LRM
are in `docs/` (expanded in phase 4 of the implementation plan).

## License

Apache-2.0. See [LICENSE](LICENSE).
