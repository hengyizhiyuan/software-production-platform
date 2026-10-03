"""Closed security-group operations bound to one Human-authorized Delivery."""

from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

from spg.domain.cloud_delivery import (
    CloudDeliveryAuthorization, CloudExposureMode, CloudOperationKind,
    CloudOperationReceipt, CloudTarget,
)


class CloudNetworkError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def ingress_description(product_id: UUID, deployment_id: UUID) -> str:
    return f"WattManagedIngressV1 product={product_id} deployment={deployment_id}"


@dataclass(frozen=True)
class EnsureWattPublicIngressV1:
    authorization: CloudDeliveryAuthorization
    deployment_id: UUID
    target: CloudTarget
    port: int

    def __post_init__(self):
        if (self.authorization.exposure_mode is not CloudExposureMode.PUBLIC or
                self.authorization.product_id is None or
                self.authorization.target.identity != self.target.identity or
                self.authorization.port != self.port or
                not 1024 <= self.port <= 65535):
            raise CloudNetworkError("PUBLIC_INGRESS_AUTHORITY_MISMATCH")

    @property
    def description(self) -> str:
        return ingress_description(self.authorization.product_id, self.deployment_id)


@dataclass(frozen=True)
class RevokeWattPublicIngressV1:
    authorization: CloudDeliveryAuthorization
    deployment_id: UUID
    target: CloudTarget
    port: int
    creation_receipt: CloudOperationReceipt

    def __post_init__(self):
        EnsureWattPublicIngressV1(self.authorization, self.deployment_id,
            self.target, self.port)
        receipt = self.creation_receipt
        if (receipt.kind is not CloudOperationKind.ENSURE_WATT_PUBLIC_INGRESS_V1 or
                not receipt.verified or receipt.network_effect != "CREATED" or
                (receipt.account_id, receipt.region_id, receipt.instance_id) !=
                    self.target.identity or
                receipt.network_rule_description != ingress_description(
                    self.authorization.product_id, self.deployment_id) or
                not receipt.security_group_id or
                not receipt.security_group_rule_id or
                not re.fullmatch(r"sg-[A-Za-z0-9]{6,64}", receipt.security_group_id) or
                not re.fullmatch(r"sgr-[A-Za-z0-9]{6,64}", receipt.security_group_rule_id)):
            raise CloudNetworkError("WATT_CREATED_RULE_EVIDENCE_REQUIRED")


@dataclass(frozen=True)
class IngressResult:
    security_group_id: str
    rule_id: str
    description: str
    effect: str
    request_id: str | None
    verified: bool
