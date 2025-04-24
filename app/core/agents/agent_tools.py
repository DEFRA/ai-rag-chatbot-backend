from langchain.tools.retriever import create_retriever_tool

from app.core.rag.vector_store import retriever

resources = [
    {
        "id": "how_to_have_your_benefits_paid",
        "title": "How to Have Your Benefits Paid",
        "url": "https://www.gov.uk/how-to-have-your-benefits-paid",
        "description": (
            "Explains how UK social security benefits are paid, including which types of bank or building society accounts "
            "can receive payments and what to do if you can’t open an account."
        ),
        "topics": [
            "benefits",
            "payment methods",
            "bank accounts",
            "social security guidance",
        ],
    },
    {
        "id": "how_to_claim_universal_credit",
        "title": "How to Claim Universal Credit",
        "url": "https://www.gov.uk/how-to-claim-universal-credit",
        "description": (
            "Step-by-step guide to checking eligibility for Universal Credit, gathering required documents, and completing "
            "the online application."
        ),
        "topics": [
            "universal credit",
            "eligibility",
            "application process",
            "income support",
        ],
    },
    {
        "id": "universal_credit_and_rented_housing_landlords",
        "title": "Universal Credit and Rented Housing: Guide for Landlords",
        "url": "https://www.gov.uk/government/publications/universal-credit-and-rented-housing--2/universal-credit-and-rented-housing-guide-for-landlords",
        "description": (
            "Advice for landlords on how Universal Credit affects rent payments, tenant responsibilities, landlord payment "
            "requests, and direct payment options."
        ),
        "topics": [
            "universal credit",
            "housing benefit",
            "landlord guidance",
            "rent payment",
        ],
    },
    {
        "id": "understanding_ai_ethics_and_safety",
        "title": "Understanding Artificial Intelligence Ethics and Safety",
        "url": "https://www.gov.uk/guidance/understanding-artificial-intelligence-ethics-and-safety",
        "description": (
            "Overview of ethical principles and safety considerations for AI development and deployment, covering "
            "transparency, fairness, accountability, and risk management."
        ),
        "topics": [
            "AI ethics",
            "safety",
            "transparency",
            "accountability",
            "risk management",
        ],
    },
]


# Build description dynamically from resource metadata
def build_tool_description(resources):
    lines = [
        "Use this tool to search UK government guidance from GOV.UK on the following topics:\n"
    ]
    for res in resources:
        lines.append(
            f"- **{res['title']}** – {res['description']}\n  [Source] {res['url']}\n"
        )
    return "\n".join(lines)


# Create retriever tool with rich description
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="gov_knowledge_base",
    description=build_tool_description(resources),
)

tools = [retriever_tool]

print("Retriever tool with GOV.UK metadata created.")
