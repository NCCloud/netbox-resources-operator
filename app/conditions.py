from apischema import serialize
from app.models import (
    StatusCondition,
    StatusConditionTypeEnum,
    StatusConditionReasonEnum,
)
from kopf import Patch


def set_condition(patch: Patch, condition: StatusCondition):
    """
    Set a condition on an object
    """

    patch.status.setdefault("conditions", [])

    serialized_condition = serialize(condition)

    # replace existing condition
    patch.status["conditions"] = [
        c for c in patch.status["conditions"] if c.get("type") != condition.type
    ] + [serialized_condition]


def set_reconciliation_conditions(patch: Patch):
    """
    Set conditions for the object creation or update
    """
    reconciliation_condition = StatusCondition(
        type=StatusConditionTypeEnum.RECONCILING.value,
        status="True",
        reason=StatusConditionReasonEnum.SPEC_CHANGED.value,
        message="Reconciling desired state",
    )
    set_condition(patch=patch, condition=reconciliation_condition)

    ready_condition = StatusCondition(
        type=StatusConditionTypeEnum.READY.value,
        status="False",
        reason=StatusConditionReasonEnum.RECONCILING.value,
        message="Reconciling desired state",
    )
    set_condition(patch=patch, condition=ready_condition)


def set_failed_condition(patch: Patch, error: str):
    error_condition = StatusCondition(
        type=StatusConditionTypeEnum.FAILED.value,
        status="True",
        reason=StatusConditionReasonEnum.ERROR.value,
        message=error,
    )
    set_condition(patch=patch, condition=error_condition)

    reconciliation_condition = StatusCondition(
        type=StatusConditionTypeEnum.RECONCILING.value,
        status="False",
        reason=StatusConditionReasonEnum.ERROR.value,
        message="The object cannot be reconciled due to an error",
    )
    set_condition(patch=patch, condition=reconciliation_condition)

    ready_condition = StatusCondition(
        type=StatusConditionTypeEnum.READY.value,
        status="False",
        reason=StatusConditionReasonEnum.ERROR.value,
        message="The object cannot be reconciled due to an error",
    )
    set_condition(patch=patch, condition=ready_condition)


def set_reconciled_condition(patch: Patch):
    """
    Set conditions after a completed reconciliation
    """
    reconciliation_condition = StatusCondition(
        type=StatusConditionTypeEnum.RECONCILING.value,
        status="False",
        reason=StatusConditionReasonEnum.COMPLETED.value,
        message="Reconciliation finished",
    )
    set_condition(patch=patch, condition=reconciliation_condition)

    ready_condition = StatusCondition(
        type=StatusConditionTypeEnum.READY.value,
        status="True",
        reason=StatusConditionReasonEnum.RECONCILED.value,
        message="Object matches the desired state",
    )
    set_condition(patch=patch, condition=ready_condition)
