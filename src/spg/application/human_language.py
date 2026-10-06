"""Fail-closed normal-language gate; explicit evidence views retain raw metadata."""
import re

_INTERNAL = re.compile(r'\b(?:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|DesignIssue|TaskContractRequest|'
    r'ProductionPlanGraph|oracle_id|basis_fingerprint|SemanticStepResult|GovernedSemanticIR|Steering|IRK|ECF|HumanDecisionNeed|TaskContract|GuidedDesign|Guided Design|Task Contract)\b|'
    r'Establish the Motive|Choose how to handle a material risk or cost|'
    r'Establish desired user value|Bound the product/system responsibility|'
    r'Shape the minimum capability model|Clarify Human/system responsibility|'
    r'Identify architecture implications|Form a reviewable bounded next-stage|'
    r'Produce the next exact change admitted|Steering evaluates the current governed|'
    r'产出下一个从当前现实准入的精确变更|对照长期成果评估可信结果|'
    r'完成已准入的长期工作|评估当前受治理的计划步骤|当前生产步骤为生产')
_ID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b[0-9a-f]{64}\b', re.I)


def language_leaks(text: str) -> bool:
    return bool(_INTERNAL.search(text) or _ID.search(text))


def require_human_language(text: str):
    if language_leaks(text):
        raise ValueError('HUMAN_LANGUAGE_LEAKAGE')
