"""Language of newly authored prose; exact source and machine identities stay intact."""

import re


def uses_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def chinese_interaction(basis) -> bool:
    return uses_chinese(basis.records[-1].content)


def exclusion_constraint(value: str, *, chinese: bool) -> str:
    return f"本次工作不包含：{value}" if chinese else f"Excluded from this Work: {value}"


def exclusion_constraint_forms(value: str) -> tuple[str, str]:
    # Fixed, source-owned projection forms, not a natural-language exclusion parser.
    return (exclusion_constraint(value, chinese=False), exclusion_constraint(value, chinese=True))
