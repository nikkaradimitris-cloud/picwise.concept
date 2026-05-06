from __future__ import annotations

from typing import Any

from picwise_contracts import (
    ContractValidationError,
    DecisionOutput,
    MissingDataState,
    validate_missing_data_states,
    validate_no_commission_ranking_fields,
    validate_no_fake_data,
)

from .arbitration import DecisionArbitrator
from .brain_selector import BrainSelector
from .candidate_adapter import ProductCandidateAdapter
from .depth_selector import DecisionDepthSelector


class PicwiseDecisionEngine:
    def __init__(self) -> None:
        self._brain_selector = BrainSelector()
        self._depth_selector = DecisionDepthSelector()
        self._candidate_adapter = ProductCandidateAdapter()
        self._arbitrator = DecisionArbitrator()

    def run(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        context_metadata: dict[str, Any] | None = None,
    ) -> DecisionOutput:
        if not query or not str(query).strip():
            raise ContractValidationError("Query is required for decision engine execution.")
        context_metadata = context_metadata or {}
        if not isinstance(context_metadata, dict):
            raise ContractValidationError("context_metadata must be a dictionary.")

        validate_no_fake_data(context_metadata)
        validate_no_commission_ranking_fields(context_metadata)
        validate_no_fake_data(candidates)
        validate_no_commission_ranking_fields(candidates)

        brain_selection = self._brain_selector.select(query, context_metadata)
        depth_selection = self._depth_selector.select(
            query=query,
            context=context_metadata,
            selected_brain=brain_selection.brain,
        )
        adapted = self._candidate_adapter.adapt_candidates(
            raw_candidates=candidates,
            selected_brain=brain_selection.brain,
        )
        arbitration = self._arbitrator.arbitrate(
            candidates=adapted,
            selected_brain=brain_selection.brain,
        )

        missing_states = self._resolve_missing_states(context_metadata)
        tracking_context = dict(context_metadata.get("tracking_context", {}))
        if not isinstance(tracking_context, dict):
            raise ContractValidationError("tracking_context in context_metadata must be a dictionary.")
        tracking_context.update(
            {
                "brain_confidence": brain_selection.confidence,
                "brain_notes": brain_selection.notes,
                "depth_confidence": depth_selection.confidence,
                "depth_notes": depth_selection.notes,
                "arbitration_notes": arbitration.notes,
                "recommended_reason": arbitration.recommendation_reason,
            }
        )

        payload = {
            "query": str(query),
            "selected_brain": brain_selection.brain.value,
            "decision_depth": depth_selection.depth.value,
            "page_title": f"4 decision-ready options for {query}",
            "choices": arbitration.selected_choices,
            "recommended_product_id": arbitration.recommended_product_id,
            "missing_data_states": [state.value for state in missing_states],
            "tracking_context": tracking_context,
        }
        return DecisionOutput.from_dict(payload)

    def _resolve_missing_states(self, context_metadata: dict[str, Any]) -> list[MissingDataState]:
        raw = context_metadata.get("missing_data_states", [MissingDataState.UNKNOWN.value])
        if not isinstance(raw, list):
            raise ContractValidationError("missing_data_states must be a list if provided.")
        validate_missing_data_states([str(state) for state in raw])
        return [MissingDataState(str(state)) for state in raw]
