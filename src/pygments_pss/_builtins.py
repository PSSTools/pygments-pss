"""Core-library names -- Annex C (``DESIGN.md`` section 6.7, plan P2.2).

**Hand-curated, not generated.** Annex C is normative but it is *prose-embedded
code*: the package bodies are interleaved with explanatory text and examples, so
a scraper picks up `and`, `shall` and `my_struct_s` alongside `urandom_range`.
The extraction was done mechanically and then filtered by hand against the
corpus's ``stdlib/`` bucket (``pss-corpus``, formerly ``tests/corpus/stdlib/``
in this repo), which carries a working implementation of the same four
packages. Anything here that neither Annex C nor that implementation
declares is a bug.

These are **library**, not language: ``Name.Builtin`` rather than
``Keyword.Type``, for types as well as functions (``DESIGN.md`` section 6.2).

Known and accepted false positive: a user-defined `print` or `read` is
highlighted as a builtin too. A ``RegexLexer`` has no scope information, and
the alternative -- highlighting nothing -- loses the case that actually helps a
reader. Documented in ``reference/deviations.md``; turn it off with
``builtins=False``.

Names deliberately **excluded**: the examples that appear inside Annex C's
prose (`color_e`, `my_struct_s`, `base_s`, `derived_s`, `sub_s`, `foo`) are not
part of the library.
"""

from __future__ import annotations

#: The four core-library packages themselves (Clause 21).
BUILTIN_PACKAGES = (
    "addr_reg_pkg",
    "executor_pkg",
    "std_pkg",
    "sync_pkg",
)

#: C.1 std_pkg -- types.
STD_TYPES = (
    "endianness_e",
    "file_handle_t",
    "file_option_e",
    "float32_s",
    "float64_s",
    "float_base_s",
    "message_verbosity_e",
    "packed_s",
    "sizeof_s",
)

#: C.1 std_pkg -- functions. Message and formatting, file I/O, randomisation,
#: and the floating-point set.
STD_FUNCTIONS = (
    # messaging
    "error",
    "fatal",
    "format",
    "message",
    "print",
    # randomisation
    "urandom",
    "urandom_range",
    # file I/O
    "file_close",
    "file_exists",
    "file_open",
    "file_read",
    "file_read_lines",
    "file_write",
    "file_write_lines",
    # floating point
    "acos",
    "acosh",
    "asin",
    "asinh",
    "atan",
    "atan2",
    "atanh",
    "ceil",
    "cos",
    "cosh",
    "exp",
    "float_exponent",
    "float_mantissa",
    "float_sign",
    "floor",
    "hypot",
    "log",
    "log10",
    "pow",
    "round",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
    "to_float",
)

#: C.2 executor_pkg.
EXECUTOR_NAMES = (
    "executor_base_c",
    "executor_c",
    "executor_claim_s",
    "executor_group_c",
    "executor_trait_s",
    "empty_executor_trait_s",
    "target_execution_unit_c",
    "target_language_e",
    "get_target_execution_unit",
    "get_target_language",
    "set_target_execution_unit",
    "set_target_language",
    "add_executor",
    "set_executor",
)

#: C.3 addr_reg_pkg -- address spaces, claims, handles and the register model.
ADDR_REG_NAMES = (
    # address spaces
    "addr_space_base_c",
    "addr_space_group_c",
    "contiguous_addr_space_c",
    "transparent_addr_space_c",
    # claims and regions
    "addr_claim_base_s",
    "addr_claim_s",
    "addr_region_base_s",
    "addr_region_s",
    "addr_trait_s",
    "empty_addr_trait_s",
    "transparent_addr_claim_s",
    "transparent_addr_region_s",
    "sized_addr_handle_s",
    # allocation modes
    "alloc_access_mode_e",
    "alloc_base_mode_s",
    "alloc_share_mode_e",
    "alloc_skip_mode_e",
    # handles and access
    "addr_handle_t",
    "addr_value",
    "addr_value_abs",
    "addr_value_solve",
    "make_handle_from_claim",
    "make_handle_from_handle",
    "add_addr_space",
    "add_region",
    "get_handle",
    "set_handle",
    "get_tag",
    # memory access
    "mem_access_desc_s",
    "read8",
    "read16",
    "read32",
    "read64",
    "read_bytes",
    "read_struct",
    "write8",
    "write16",
    "write32",
    "write64",
    "write_bytes",
    "write_struct",
    "write_masked",
    # register model
    "reg_access",
    "reg_base_c",
    "reg_c",
    "reg_group_c",
    "reg_sized_c",
    "get_mnemonic_of_instance",
    "get_mnemonic_of_instance_array",
    "get_mnemonic_of_path",
    "get_offset_of_instance",
    "get_offset_of_path",
    "read_val",
    "write_val",
    "write_val_masked",
    "write_field",
    "write_fields",
    "use_symbolic_reg_names",
)

#: C.4 sync_pkg.
SYNC_NAMES = (
    "channel_c",
    "node_s",
)

#: Enumeration members are **deliberately not matched.** They were curated and
#: then dropped: `NONE`, `LOW`, `HIGH`, `FULL`, `READ`, `RANDOM`, `SHARED`,
#: `SKIP` and `C` are exactly the names a user's own enum uses, and PSS
#: capitalises enum members by convention, so matching them would mis-highlight
#: user code far more often than it would help. The types that contain them
#: (`endianness_e`, `reg_access`, ...) are matched, which is where the reader
#: gets the signal. Recorded in reference/deviations.md.
#:
#: Also excluded for the same reason: `sync_pkg`'s `channel_c` methods `get`,
#: `put`, `try_get`, `try_put`, `read` and `write`. `print` is kept despite the
#: risk -- DESIGN.md section 6.7 names it as the case that justifies the
#: feature.

#: Every core-library name, as a set for O(1) lookup from the identifier rule.
BUILTINS = frozenset(
    BUILTIN_PACKAGES
    + STD_TYPES
    + STD_FUNCTIONS
    + EXECUTOR_NAMES
    + ADDR_REG_NAMES
    + SYNC_NAMES
)
