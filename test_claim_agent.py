
from app.agents.caim_analysis_agent import ClaimAnalysisAgent
from app.services.azure_openai import AzureOpenAIService


llm_service = AzureOpenAIService()

agent = ClaimAnalysisAgent(
    llm_service=llm_service
)

sample_state = {
    "validation_result": {
        "validation_status": "needs_review",
        "total_checks": 2,
        "passed_checks": 0,
        "failed_checks": 2,
        "results": [
            {
                "rule": "patient_name_consistency",
                "status": "failed",
                "severity": "critical",
                "message": "Patient name mismatch detected",
                "values": {
                    "hospital_bill": "Arjun Kumar Reddy",
                    "laboratory_report": "Ananya Priya Rao"
                }
            },
            {
                "rule": "patient_id_consistency",
                "status": "failed",
                "severity": "critical",
                "message": "Patient ID mismatch detected"
            }
        ]
    }
}

result = agent.execute(sample_state)

print(result)
