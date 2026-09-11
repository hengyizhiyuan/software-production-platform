"""Recovery classification for interrupted native execution."""

from __future__ import annotations

from spg.domain.native_execution import (
    CheckpointBundleRecord,
    EffectCondition,
    ExecutionEffectRecord,
    RecoveryClassification,
)


class NativeRecoveryClassifier:
    """Classify observed Reality before any successor Attempt is admitted."""

    def classify(
        self,
        *,
        checkpoint: CheckpointBundleRecord | None,
        effects: tuple[ExecutionEffectRecord, ...],
        workspace_available: bool,
        contract_satisfied: bool,
    ) -> RecoveryClassification:
        if any(
            effect.condition in {EffectCondition.STARTING, EffectCondition.ACTIVE, EffectCondition.UNKNOWN}
            for effect in effects
        ):
            return RecoveryClassification.EFFECT_UNRESOLVED
        if contract_satisfied:
            return RecoveryClassification.COMPLETE
        if checkpoint is None and not effects:
            return RecoveryClassification.NO_EFFECT
        if not workspace_available:
            return RecoveryClassification.LOST
        if checkpoint is not None:
            return RecoveryClassification.PARTIAL
        return RecoveryClassification.STALE
