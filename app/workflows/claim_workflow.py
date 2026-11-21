
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from app.workflows.claim_state import ClaimWorkflowState

from app.agents.validation_agent import ClaimValidationAgent
from app.agents.caim_analysis_agent import ClaimAnalysisAgent
from app.agents.decision_agent import ClaimDecisionAgent


logger = logging.getLogger(__name__)


class ClaimWorkflowOrchestrator:

    def __init__(
        self,
        validation_agent: ClaimValidationAgent,
        analysis_agent: ClaimAnalysisAgent,
        decision_agent: ClaimDecisionAgent,
        checkpointer
    ):

        self.validation_agent = validation_agent
        self.analysis_agent = analysis_agent
        self.decision_agent = decision_agent
        self.checkpointer = checkpointer

        self.workflow = self._build_workflow()

    def _build_workflow(self):

        builder = StateGraph(ClaimWorkflowState)

        builder.add_node(
            "validation",
            self.validation_agent.execute
        )

        builder.add_node(
            "analysis",
            self.analysis_agent.execute
        )

        builder.add_node(
            "decision",
            self.decision_agent.execute
        )

        builder.add_node(
            "human_review",
            self._human_review
        )

        builder.add_edge(START, "validation")

        builder.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {
                "analysis": "analysis",
                "decision": "decision"
            }
        )

        builder.add_edge("analysis", "decision")

        builder.add_conditional_edges(
            "decision",
            self._route_after_decision,
            {
                "human_review": "human_review",
                "end": END
            }
        )

        builder.add_edge("human_review", END)

        return builder.compile(
            checkpointer=self.checkpointer
        )

    @staticmethod
    def _route_after_validation(state):

        status = state.get(
            "validation_result", {}
        ).get("validation_status")

        if status == "incomplete":
            return "decision"

        return "analysis"

    @staticmethod
    def _route_after_decision(state):

        if state.get("workflow_status") == "needs_review":
            return "human_review"

        return "end"

    def _human_review(self, state):

        logger.info(
            "Claim waiting for human review: %s",
            state.get("claim_id")
        )

        reviewer_input = interrupt({
            "message": "Claim requires manual review",
            "claim_id": state.get("claim_id"),
            "validation_result": state.get("validation_result"),
            "analysis_result": state.get("analysis_result"),
            "allowed_actions": [
                "approved",
                "rejected",
                "requires_information"
            ]
        })

        action = reviewer_input["action"]

        logger.info(
            "Reviewer decision received: %s",
            action
        )

        status_mapping = {
            "approved": "approved",
            "rejected": "rejected",
            "requires_information": "requires_information"
        }

        if action not in status_mapping:
            raise ValueError("Invalid reviewer action")

        return {
            "review_decision": action,
            "reviewer": reviewer_input["reviewer"],
            "review_comments": reviewer_input.get("comments", ""),
            "workflow_status": status_mapping[action],
            "next_action": action
        }

    def execute(self, initial_state, thread_id):

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        logger.info(
            "Starting claim workflow: %s",
            thread_id
        )

        return self.workflow.invoke(
            initial_state,
            config=config
        )

    def resume(self, thread_id, reviewer_input):

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        logger.info(
            "Resuming claim workflow: %s",
            thread_id
        )

        return self.workflow.invoke(
            Command(resume=reviewer_input),
            config=config
        )
