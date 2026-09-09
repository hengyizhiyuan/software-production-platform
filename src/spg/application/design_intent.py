"""Conservative Watt-native fallback for Design Intent Framing."""

from __future__ import annotations

from spg.domain.design_intent import (
    DesignCollaborationMode,
    DesignIntentFrame,
    DesignObjectType,
    DesignScopeLevel,
)


def frame_design_intent_text(
    text: str,
    *,
    desired_outcome: str | None = None,
) -> DesignIntentFrame:
    """Frame explicit wording without pretending ambiguous optimization is a product."""

    subject = " ".join(text.split()).strip()
    normalized = subject.casefold()
    system_markers = (
        "system",
        "platform",
        "application",
        " app",
        "tool",
        "系统",
        "平台",
        "应用",
        "工具",
        "后台",
    )
    feature_markers = (
        "add ",
        "feature",
        "capability",
        "增加",
        "新增",
        "功能",
        "能力",
    )
    existing_markers = (
        "existing",
        "current",
        "现有",
        "已有",
        "当前",
    )
    activity_markers = (
        "campaign",
        "launch event",
        "livestream event",
        "策划一次",
        "发布直播",
        "运营活动",
    )
    process_markers = ("process", "workflow", "流程", "机制")
    review_markers = ("review", "analysis", "investigate", "评审", "分析", "调研")
    ambiguous_improvement_markers = (
        "improve efficiency",
        "optimize efficiency",
        "优化研发效率",
        "提升研发效率",
    )

    has_system = any(marker in normalized for marker in system_markers)
    if any(marker in normalized for marker in ambiguous_improvement_markers) and not has_system:
        object_type = DesignObjectType.UNKNOWN
        scope = DesignScopeLevel.STRATEGIC
        mode = DesignCollaborationMode.EXPLORATION
        ambiguities = (
            "The desired change could be a software product, process change, AI workflow, or organizational improvement.",
        )
        confidence = 0.45
    elif (
        any(marker in normalized for marker in existing_markers)
        and any(marker in normalized for marker in feature_markers)
    ):
        object_type = DesignObjectType.FEATURE
        scope = DesignScopeLevel.CAPABILITY
        mode = DesignCollaborationMode.EXECUTION
        ambiguities = ()
        confidence = 0.9
    elif any(marker in normalized for marker in activity_markers) and not has_system:
        object_type = DesignObjectType.OPERATIONAL_ACTIVITY
        scope = DesignScopeLevel.CAPABILITY
        mode = DesignCollaborationMode.DESIGN
        ambiguities = ()
        confidence = 0.9
    elif any(marker in normalized for marker in review_markers) and not has_system:
        object_type = DesignObjectType.REVIEW_ANALYSIS
        scope = DesignScopeLevel.CAPABILITY
        mode = DesignCollaborationMode.REVIEW
        ambiguities = ()
        confidence = 0.85
    elif any(marker in normalized for marker in process_markers) and not has_system:
        object_type = DesignObjectType.BUSINESS_PROCESS
        scope = DesignScopeLevel.CAPABILITY
        mode = DesignCollaborationMode.DESIGN
        ambiguities = ()
        confidence = 0.75
    else:
        object_type = DesignObjectType.PRODUCT_SYSTEM
        scope = DesignScopeLevel.PRODUCT
        mode = DesignCollaborationMode.DESIGN
        ambiguities = ()
        confidence = 0.8 if has_system else 0.6

    business_context = None
    if "推广 watt" in normalized or "promote watt" in normalized:
        business_context = "Support Watt promotion and related operations."
    return DesignIntentFrame(
        design_subject=subject,
        object_type=object_type,
        business_context=business_context,
        desired_outcome=desired_outcome,
        scope_level=scope,
        collaboration_mode=mode,
        candidate_assumptions=(
            ()
            if confidence >= 0.75
            else ("The current object classification is provisional.",)
        ),
        ambiguities=ambiguities,
        confidence=confidence,
    )
