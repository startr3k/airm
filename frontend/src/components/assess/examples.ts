export interface Example {
  id: string;
  label: string;
  hint: string;
  description: string;
  is_agentic: boolean;
  customer_facing: boolean;
  tools_accessible: string[];
  deployment_pattern: "build" | "onboard" | "onboard_with_customisation";
}

export const EXAMPLES: Example[] = [
  {
    id: "chatbot",
    label: "Internal knowledge chatbot",
    hint: "expected: low",
    description:
      "An internal knowledge chatbot for staff. It uses retrieval-augmented generation over our HR handbook, IT policies and internal procedures, and answers employee questions with a citation to the source document. Staff-only, no customer access, no personal data beyond the employee's own question.",
    is_agentic: false,
    customer_facing: false,
    tools_accessible: [],
    deployment_pattern: "onboard_with_customisation",
  },
  {
    id: "claims",
    label: "Claims automation with HITL",
    hint: "expected: medium",
    description:
      "An insurance claims triage model that scores incoming motor claims for likely fraud and routes them to a review queue. Every declined or escalated claim is decided by a human assessor, who sees the score and the contributing factors.",
    is_agentic: false,
    customer_facing: true,
    tools_accessible: [],
    deployment_pattern: "build",
  },
  {
    id: "agentic-rm",
    label: "Agentic RM assistant",
    hint: "expected: high",
    description:
      "A multi-agent assistant for relationship managers at a private bank. One agent researches client portfolios and market data, another drafts investment proposals, and a third can email the client and place trades through our execution desk API within preset limits. The RM reviews proposals, but trades under SGD 50,000 execute automatically.",
    is_agentic: true,
    customer_facing: true,
    tools_accessible: [
      "search_market_data",
      "send_client_email",
      "execute_trade",
      "update_crm_record",
    ],
    deployment_pattern: "build",
  },
];
