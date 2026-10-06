"""Fail-closed normal-language gate; explicit evidence views retain raw metadata."""
import re

_INTERNAL = re.compile(r'\b(?:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|DesignIssue|TaskContractRequest|'
    r'ProductionPlanGraph|oracle_id|basis_fingerprint|SemanticStepResult|GovernedSemanticIR)\b|'
    r'Establish the Motive|Choose how to handle a material risk or cost|'
    r'Establish desired user value|Bound the product/system responsibility|'
    r'Shape the minimum capability model|Clarify Human/system responsibility|'
    r'Identify architecture implications|Form a reviewable bounded next-stage|'
    r'Produce the next exact change admitted|Steering evaluates the current governed')
_ID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b[0-9a-f]{64}\b', re.I)


def language_leaks(text: str) -> bool:
    return bool(_INTERNAL.search(text) or _ID.search(text))


def require_human_language(text: str):
    if language_leaks(text):
        raise ValueError('HUMAN_LANGUAGE_LEAKAGE')
