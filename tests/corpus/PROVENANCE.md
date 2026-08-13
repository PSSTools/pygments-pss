# Corpus provenance

Vendored, not path-referenced, so the suite runs standalone (`DESIGN.md` §8.1,
plan P-D3). These files are **frozen test input**: do not reformat them, do not
"fix" their PSS, and re-vendor only deliberately. A corpus that changes under
you is worse than one that ages.

Remote URLs are given as `git.dvkit.org` paths; the self-hosted instance is
also reachable over the internal network, which must not be named in a tracked
file.

| Directory | Source | Commit | What it contributes |
| --- | --- | --- | --- |
| `example2/` | `psstools/example` — `2/src/pss/` (working tree, not a git checkout) | n/a, vendored 2026-08-13 | Hand-written idiomatic PSS: components, actions, activities, register/memory models. |
| `stdlib/` | `zuspec/zuspec-fe-pss` — `src/stdlib/` | `62be6eeded41656a881bc6bafd58e9efc9474e96` | The PSS core library itself (`std_pkg`, `executor_pkg`, `addr_reg_pkg`, `sync_pkg`, `packed_s`). Substitutes for the plan's T2.2 source, `tests/patterns/`, which no longer exists in that repo. Higher value than what it replaces: it is the exact vocabulary P2.2 has to recognise. |
| `peakrdl/` | `psstools/peakrdl-pss` — `tests/golden/expect/` | `f351df80bfe9b7a9ddaa0491310886eabb21bf23` | Machine-generated, register-model idioms — a different style from anything hand-written. |
| `language-ref/` | `psstools/pss-skills` — `skills/pss-language-ref/examples/` | `f1ed60279e4b3c7fa961e398b505563c101865f9` | Feature-targeted examples written against the LRM. |
| `pss31/` | authored here | — | 3.1-only surface (T2.5). |
| `lexical/` | authored here | — | Clause 4 lexical torture (T2.6). |
| `pathological/` | authored here | — | Deliberately broken input (T2.7). Excluded from the no-`Error` rule. |
