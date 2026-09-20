# Framework notes

<!-- GENERATED FILE -- do not edit by hand.
     Regenerate with: python -m mindforge_assess.ingest.notes -->

What the tool encodes from *AI Risk Management: Operationalisation Handbook*
(The MindForge Consortium, January 2026).

Page numbers are **printed** page numbers — what a reader sees in the footer.
The PDF's physical pages run 7 ahead (`pdf_page = printed_page + 7`).

## Provenance

| | |
| --- | --- |
| Source PDF | `MindForge AI Risk Management Operationalisation Handbook.pdf` |
| SHA-256 | `c5055bacf114b7413b476ba0f3e8366a74c39fa7f049cfae7318615665f16486` |
| Physical pages | 173 |
| Extraction model | `claude-opus-5` |
| Extracted | 2026-09-20T09:30:26+00:00 |
| Pack built | 2026-09-20T09:51:55+00:00 |
| Sections present | 9 of 9 |

Verified by `claude-opus-5` on 2026-09-20T09:51:48+00:00: **0** blocking failure(s). See [verification_report.md](../backend/framework/verification_report.md).

## What was extracted

| Item | Count |
| --- | --- |
| Dimensions | 7 |
| Taxonomy risks | 41 |
| Materiality factors | 11 |
| Matrix cells | 9 |
| Oversight modes | 3 |
| Sampling methodologies | 3 |
| Interruption controls | 12 |
| Metrics | 53 |
| Guardrails | 38 |
| Considerations | 17 |
| Implementation practices | 60 |
| Illustrations | 9 |
| Agentic risk factors | 12 |

## Scope: what counts as AI (Section 1.1)

> For the purposes of this Handbook, the MindForge consortium focuses on two key characteristics to help practitioners consistently identify and manage AI: (1) AI learns and/or infers from inputs to generate output such as estimates, predictions, content, summaries, recommendations, or decisions; (2) AI excludes calculators or tools whose outputs are solely based on predefined programming or rules. These characteristics generalise MAS' proposed Guidelines definition: "AI includes use cases involving models or systems that learn and/or infer from inputs to generate outputs such as estimates, predictions, content, summaries, recommendations, or decisions that may influence physical or virtual environments, and vary in their levels of autonomy and adaptiveness after deployment. Calculators or… (p. 13)

Out of scope — an `ai_in_scope: false` short-circuit in the assessor:

- Traditional rule-based software. — Outputs are solely based on predefined programming or rules, so it does not meet the AI definition. (p. 13)
- Macros and other deterministic automations, including some types of Robotic Process Automation (RPA). — Deterministic automation whose outputs follow predefined logic rather than learning or inference. (p. 13)
- Chatbots that are menu-based or rules-based, such as those using keyword identification. — Rules-based rather than learning/inferring from inputs. (p. 13)
- Pre-defined data processing logic. — Outputs are solely based on predefined programming logic or rules. (p. 13)
- Calculators or tools whose outputs are solely based on predefined programming logic or rules. — Expressly excluded by the MAS definition adopted by the Handbook. (p. 13)
- Non-AI functionalities of a larger software system (e.g. a customer relationship management system where only a Gen AI note/email summarisation feature is AI-supported) — AI governance and risk management applies only to those outputs or behaviours of the system affected or influenced by its AI components or functionalities. (p. 15)

In scope:

- Linear or logistic regression models. (p. 13)
- Models using machine learning and its derivative techniques such as deep learning, transformers (LLMs), and diffusion models. (p. 13)
- Computer vision models, including optical character recognition features that use computer vision models. (p. 13)
- Virtual assistants based on language models. (p. 13)
- Agent and agentic systems that use language models and other AI tools. (p. 13)

| Term | Definition | Page |
| --- | --- | --- |
| Model | An AI model, which is a mathematical or logical representation mapping inputs to outputs, is the foundation of modern AI technology. An AI model is any model which meets the definition of AI. Models output estimates, forecasts, or projections related to real-world phenomena. E.g. A function predict… | 15 |
| System | An AI system includes an AI model as well as other software components that allow models to be used in real-world applications. A system can contain many software features, and potentially many models that interact via software. E.g. a spreadsheet with user data plus a statistical model saved as a… | 15 |
| Use Case | An AI use case is the specific, real-world context in which an AI system is intentionally used. Use cases are crucial for understanding the impact, risks, and functioning of systems. E.g. Using AI to consider several data points about a customer to underwrite loan risk is a use case. | 15 |
| AI governance and risk management | Together, a set of interdisciplinary activities for: (1) managing AI-specific risks posed to the enterprise, its stakeholders, and society; (2) ensuring that the use of AI adheres to an FI's principles, especially Fairness, Ethics, Accountability, and Transparency; and (3) ensuring that the use of… | 14 |
| AI-specific risks | New or enhanced risks arising from AI use that go beyond those of traditional software use in the context of an FI. | 8 |
| Considerations | The operative unit of the Handbook (17 in total); each Consideration is a thematic recommendation that will support an FI in operationalising AI governance and risk management, grouped thematically into Subsections. | 9 |
| Practices | Specific actions under each Consideration that, when taken collectively and appropriately to the FI's context, can implement the Consideration; each is accompanied by long-form 'Operationalisation Guidelines' text. | 9 |
| Executives | Decision-makers and leaders (an intended audience within an FI). | 9 |
| Builders | Software developers, data engineers, data scientists, AI practitioners, systems integrators, and other technical specialists involved in the development, deployment, and use of AI. | 9 |
| Custodians | Employees in oversight, governance, enablement, and risk management roles in an FI who apply AI governance and risk management policies and procedures and manage AI risks, either directly or in an enabling capacity such as talent, legal, or technology. | 9 |
| Use Case Owners | Employees who are accountable for an AI use case. | 9 |
| Business Users | Employees who use or apply AI use cases in the course of their business responsibilities. | 9 |
| MindForge AI Lifecycle | Five stages: Use Case Context and Design; Data Acquisition and Processing; Onboarding, Build & Validation; Deployment; Usage, Monitoring & Change Management. These stages do not always proceed in a linear fashion and progression between them is frequently iterative. | 16 |

## Inherent risk materiality (Section 2.4)

| Factor | What it covers | Page |
| --- | --- | --- |
| **Monetary and financial impact** | The quantitative potential for an AI to impact an FI by causing losses, incurring costs, or resulting in foregone revenue (such as through lost trust or damaged relationships). Sits under the broader criterion 'Impact of the AI use case on the FI, its custome… | 47 |
| **Severity and probability of impact on different stakeholders, including individuals** | The potential for the use case to impact stakeholders – whether internal or external – in significant ways. Impact can also be affected by the volume and scope of usage, such as the number of people that interact with it or its outputs. | 47 |
| **Reputational risk** | The potential for AI use to generate controversy or negative publicity for an FI, even when it is legally compliant. | 47 |
| **Options for recourse** | The extent to which people impacted by an AI can seek effective remediation or challenge the AI's decisions. A use case with fewer options for recourse can have further impacts and be riskier. | 47 |
| **Regulatory impact** | The potential for AI use to engender compliance risk or regulatory penalties. | 47 |
| **Use of personal data** | The extent to which sensitive personal data is implicated by the AI use, which could potentially create opportunities for unjustified bias or for potential data loss or leakage. | 47 |
| **Complexity of the AI in use** | Under the criterion 'Complexity or novelty of the AI use case': the use of multiple datasets, complex architectures (e.g. LLMs), multiple models in concert (e.g. agentic AI), or other data or computational characteristics that can limit their interpretability… | 47 |
| **Extent of automation of process of AI-driven decision-making** | Under the criterion 'The degree of the FI's reliance on the AI use case': the dependency on an AI to supplement or substitute for human decision-making, which can increase the scope of that AI's impact. AI that is customer-facing without a human in the loop c… | 47 |
| **Control over credit or investment decisions (illustrative flowchart/scoring criterion)** | Illustrative criterion in Figure 2.4.2: whether the use case controls credit or investment decisions, or provides material inputs to such decisions. Scores 10 in the illustrative scoring method; a 'Yes' leads directly to High Risk in the flowchart method. The… | 49 |
| **Customer service support / sentiment analysis (illustrative flowchart/scoring criterion)** | Illustrative criterion in Figure 2.4.2: whether the use case supports customer service by providing recommended messages/actions or analysing customer sentiment. Scores 5 in the illustrative scoring method; a 'Yes' leads to Medium Risk in the flowchart method. | 49 |
| **Risk-weighted materiality threshold (illustrative flowchart/scoring criterion)** | Illustrative criterion in Figure 2.4.2: whether the use case has a risk-weighted materiality (cumulative cost of all modes of failure multiplied by their probability of occurrence) over a monetary threshold — over $500k in the flowchart method; in the scoring… | 49 |

**Combining factors:** The handbook does not prescribe a single combination rule; each FI is responsible for determining criteria and establishing discrete tiers, with tiers explicitly defined and unambiguous so they can be consistently applied across the FI. It names two common approaches that can also be combined: the flowchart method (Use Case Owners answer straightforward, binary questions about the use case and its design in a sequence, which routes to a tier — effectively a highest-wins sequential triage) and the scoring method (developers complete a full questionnaire, with responses resulting in numerical s…

| Tier | Printed as | Definition | Page |
| --- | --- | --- | --- |
| `low` | Low | One of the three tiers in the commonly used tiered approach ('Low', 'Medium', or 'High'). In the illustrative scoring method, a total of 0-4 points is Low Risk; in the flowchart method, a use case that is not credit/investment-related, not… | 48 |
| `medium` | Medium | Middle tier in the tiered approach. In the illustrative scoring method a total of 5-9 points is Medium Risk. Examples of medium residual risk materiality include automated client sentiment analysis for relationship management, personal fin… | 46 |
| `high` | High | Highest tier in the tiered approach. In the illustrative scoring method a total of 10+ points is High Risk; in the flowchart method, controlling credit or investment decisions (or providing material inputs to them) yields High Risk. An exa… | 46 |

### Figure 2.4.3: inherent → residual (p. 51)

_Figure 2.4.3: Illustrative Approach to Residual Risk Materiality Assessment Based on Inherent Risk Materiality_

| Evaluation result \ Inherent materiality | **low** | **medium** | **high** |
| --- | --- | --- | --- |
| Min. | Low Risk | Medium Risk | High Risk |
| Exceeds Min. | Low Risk | Medium Risk | High Risk |
| Best Practice | Low Risk | Low Risk | Medium Risk/High Risk |

> Use cases that fail to meet minimums do not proceed.

> (Depending on the FI's risk tiers and risk tolerance, some use cases may always have a high residual risk) — printed against high inherent / best practice (printed beneath the 'Medium Risk/High Risk' cell in the high inherent risk materiality column)

**How residual materiality is derived:** Residual risk materiality is assessed after controls and guardrails have been implemented (typically at the end of build/onboarding and prior to deployment), by qualitatively and/or quantitatively assessing the use case's behaviour in a setting representative of its intended real use with all guardrails applied. FIs define a methodology for considering both the results of this assessment and the inherent risk materiality to assign a tier of residual risk materiality. Assessment results can be rated against the use case's KPIs as meeting minimal acceptance thresholds, exceeding them, or meeting a high, industry-leading standard of performance; use cases that fail to meet minimums do not proceed. Figure 2.4.3 gives a notional matrix: a low inherent risk use case stays Low Risk regardless of evaluation result; a medium inherent use case is Medium at 'Min.' and 'Exceeds Min.' but Low at 'Be…

## Risk dimensions (Appendix B)

| Dimension | Risks | ABS top-10 | Page |
| --- | --- | --- | --- |
| **Fairness & Bias** | 2 | 2 | 133 |
| **Ethics** | 4 | 1 | 133 |
| **Accountability & Governance** | 5 | 4 | 133 |
| **Transparency** | 4 | 0 | 134 |
| **Legal & Regulatory** | 8 | 0 | 135 |
| **Robustness & Stability** | 11 | 4 | 136 |
| **Cyber & Data Security** | 7 | 0 | 137 |

### Fairness & Bias

- **Unrepresentative or biased data inputs** **[ABS top-10]** — Data is biased against, or unevenly represents, certain individuals or groups of individuals, which can produce biased model outputs. (p. 133)
- **Adverse or inappropriate impact to individuals and groups** **[ABS top-10]** — Models generate outputs that can be detrimental or inappropriate for individuals or groups. (p. 133)

### Ethics

- **Value misalignment** — Gen AI services, outputs and/or uses do not align with corporate or societal values. (p. 133)
- **Environmental sustainability impact** — Environmental impact of running LLMs, especially increased carbon emissions which impact the corporate social responsibility and ESG outcomes for the organisation. (p. 133)
- **Dark patterns** — Generation of synthetically created deceptive or manipulative content that may trick or mislead users into taking certain actions without fully understanding the consequences (example, nudging children towards certain content or services). (p. 133)
- **Toxic and offensive outputs** **[ABS top-10]** — Outputs produced contain harmful, offensive, hateful, discriminatory, violent, racist, sexist or nudity-related information. (p. 133)

### Accountability & Governance

- **Lack of AI risk awareness** **[ABS top-10]** — Insufficient education or reskilling resulting in undertrained resources lacking awareness of the unique risks involved with Gen AI. Also, over-reliance on Gen AI can lead to an erroneous, biased, or misleading outputs being accepted without adequate scrutiny… (p. 133)
- **Lack of third-party accountability** — Organisation has limited control or oversight over the development, modification and decision-making process for Gen AI models/services from third-party providers. (p. 134)
- **Lack of use case, data and model governance** **[ABS top-10]** — Failure to implement and enforce principles, guidelines, protocols and controls to proactively manage risks, and ensure traceability and responsibility in cases of undesirable outcomes. (p. 134)
- **Inadequate human oversight** **[ABS top-10]** — Insufficient human-in-the-loop or oversight, limiting recourse to human correction or intervention in the event of a failure or when generating content with risk levels requiring human validation. (p. 134)
- **Inadequate feedback and recourse mechanisms** **[ABS top-10]** — No mechanism to provide feedback or seek recourse for those impacted by harmful or biased outputs, and no consequence for the system's developers or owners for any negative outcomes. (p. 134)

### Transparency

- **Unclear output accuracy** — The level of accuracy needed for the proposed Gen AI use case outcome is not clear and cannot be validated. (p. 134)
- **Unclear provenance for training/test data** — The data used to train and test the model cannot be convincingly and comprehensively traced, presenting challenges for audit, disclosure, and potentially compliance, as well as posing the risk of the FI not having the right to use the data. (p. 134)
- **Lack of explainability** — Challenge of understanding how the Gen AI modelling techniques influence model behaviour and outputs. (p. 134)
- **Anthropomorphism** — The characteristic of Gen AI to mimic human characteristics in its output, enhancing the risk that users may find the outputs of Gen AI inappropriately convincing or may easily come under the impression that they are interacting with a human instead of a mach… (p. 134)

### Legal & Regulatory

- **Inability to ensure location compliance for model hosting and data processing** — Inability to ensure adherence to FM hosting and data processing regulations that mandate the storage and processing of data within specific geographic boundaries or jurisdictions (p. 135)
- **Unclear data ownership** — Ownership of data used to train the Gen AI model and data created by the Gen AI model is unclear, leading to additional legal, commercial and privacy risks. (p. 135)
- **Unauthorised data transfer and storage** — Data is transported and stored on unauthorised systems as per the licensing terms or organisational policies. (p. 135)
- **Breach or misalignment with regulatory or organisational standards** — The model and its outputs fail to meet legal or regulatory requirements, organisational practices or values in how the business operates. (p. 135)
- **IP infringement** — Data provided as input to a Gen AI system or product is used to create an output/content that violates IP rights owned by another individual, organisation, or entity. (p. 135)
- **Unavailability of IP protection** — The outputs of Gen AI built on FMs are not afforded IP protection such as copyright or trademarks due to a lack of legal clarity over IP protection for AI-generated content. (p. 135)
- **Inadequate privacy protection** — Inadequate protection of or originally misclassified data that can result in the processing and use of personal or sensitive data, which lacks legal or ethical justification. (p. 135)
- **Unclear data retention and deletion** — Lack of clarity on the policy around retention of personal, sensitive, or confidential data of data subjects. (p. 135)

### Robustness & Stability

- **Hallucination/ Fabrication/ Confabulation** **[ABS top-10]** — The models produce outputs that are not grounded on any source content or convincingly contradict the source content due to lack of understanding of real-world views. This can have an adverse impact on social groups or may constitute grounds for libel. They m… (p. 136)
- **Overconfidence** **[ABS top-10]** — The characteristic of Gen AI models to produce convincing outputs that do not properly account for the complexity, uncertainty, or contradiction in their sources. This leads to the potential to present false information as factual, or uncertain information as… (p. 136)
- **Training data or inputs not fit for purpose** — Training data used in model is not representative of the geographical and cultural context where the model will be used or not aligned to the system's intended goal, leading to incorrect outputs or conclusion. (p. 136)
- **Lack of continuous monitoring** — Absence of ongoing and systematic surveillance on how Gen AI systems are performing, how they are utilised, and on various parties to ensure they are in accordance with intended purposes, ethical guidelines and regulatory requirements. (p. 136)
- **Insufficient data quality** — Low-quality or noisy data used for training could result in poor model performance, increased debugging efforts, and higher development costs. Likewise, extensive use of synthetic data could result in data sets underexposed to noise and real-world complexity… (p. 136)
- **Model staleness** — Data used to train the model becomes outdated and irrelevant due to changes in its statistical properties over time, leading to the model developing ingrained biases, reduced accuracy and performance. (p. 136)
- **Insufficient model accuracy/ soundness** **[ABS top-10]** — The model outputs are inaccurate or does not meet the performance thresholds required to ensure fit for purpose. (p. 137)
- **Model degradation from unexpected use** **[ABS top-10]** — A wider range of unexpected usage patterns due to the broad capabilities of Gen AI models create outcome instability or unexpected failure modes. (p. 137)
- **Inadequate operational resilience** — Operational resilience or service continuity plans increase in complexity due to the broad set of services and capabilities of Gen AI. (p. 137)
- **Unmet architectural requirements** — Inadequate architectural requirements due to technology, cost or people constraints, leading to technical debt and hindering the scalability, robustness and long-term viability of the Gen AI system. (p. 137)
- **Lack of reproducibility** — Models that have the same parameters and identical inputs may generate different outputs. This causes challenges to reproduce a specific output and determine the accuracy in the variations of the output. (p. 137)

### Cyber & Data Security

- **Unintentional inappropriate or illegal use** — Consumers or employees use Gen AI for inappropriate or illegal activities unintentionally with liability remaining with the FI. (p. 137)
- **Data poisoning** — Deliberate manipulation of the model by a malicious actor, either through the introduction of malicious data at the point of initial training or during the course of use. This can lead to security vulnerabilities or inaccurate and harmful outputs. (p. 137)
- **Adversarial model manipulation** — Deliberate manipulation of a Gen AI system's behaviour by a malicious party with access to its FM. This can lead to undesirable or unpredictable behaviour, including inaccurate or harmful outputs. (p. 137)
- **Prompt injection** — The use of carefully designed prompts to encourage a Gen AI system to circumvent its programmed guardrails or filters. This type of attack, if successful, allows malicious actors to generate content that an FI explicitly sought to disallow. Prompt injection a… (p. 138)
- **Re-identification** — Possibility of de-identified records/ data being able to be re-identified mostly with malicious intent. This risk is related to "model inference attacks" (below) but is distinct in that it refers to data released in the normal course of operations, whereas mo… (p. 138)
- **Data leakage** — Model outputs or the model development/ training/fine-tuning process inadvertently reveal sensitive, confidential or personal data to an unauthorised user. This can occur unwittingly – when innocuous prompts produce sensitive outputs – or through prompt injec… (p. 138)
- **Model inference attacks** — Inference attacks including submitting carefully crafted input and analysing the corresponding output to reveal the membership, attributes or features about individuals in the training datasets increase in severity due to model's ability to respond to natural… (p. 138)

## Human oversight modes (Section 3.1)

| Mode | Printed as | Definition | Page |
| --- | --- | --- | --- |
| `human_in_the_loop` | Human in the Loop | Where an employee retains full control of the use case and either approves or executes actions at crucial points in operation. This may take the form of an employee reviewing AI-generated customer service emails before approving them for s… | 70 |
| `human_over_the_loop` | Human over the Loop | The AI use case produces outputs or actions where an employee has the option to modify or overrule its outputs or intervene in its operations but is not required to take any action in the course of normal operation. This includes situation… | 70 |
| `human_out_of_the_loop` | Human out of the Loop | The AI use case produces outputs without direct involvement from an employee, such as in an autonomous chatbot. While this means that the AI can take actions autonomously, it does not imply the absence of other forms of oversight, such as… | 71 |

## Monitoring and interruption (Sections 3.4–3.5)

**Table 3.5.1**

| Method | Description | Page |
| --- | --- | --- |
| Targeted High-Frequency Review | High-frequency reviews are conducted more frequently, using a representative sample of outputs. This ensures that outputs meet required standards and allows the use case team to take remediation action quickly if issues occur. | 103 |
| Lower-Frequency Review | Human reviews can be done less frequently on a representative sample of the AI's output if the use-case has a lower risk materiality. This helps to reduce unnecessary governance effort. | 103 |
| Threshold-Based Review | Threshold-based reviews do not involve human oversight in the course of normal operation, but may trigger a human review when certain conditions are met (such as a breach of risk metric thresholds). | 103 |

**Interruption controls** (what an agentic use case must have):

- **Kill switch (deactivation)** — A safeguard to deactivate the AI use case where it breaches risk thresholds or exhibits undesirable behaviour, ensuring no further harm while the issue is investigated; FIs can consider testing it prior to deployment. (p. 93)
- **Rollback to a previous stable version** — Contingency measure to revert the model to a previous, stable version when thresholds are breached or undesirable behaviour occurs. (p. 93)
- **Third-party contingency planning** — Applying existing contingency planning measures for third party software, proportionately planning for service interruptions, performance degradations, or support discontinuation of third party AI products/services. (p. 93)
- **Escalation process on threshold breach** — The monitoring plan specifies the escalation process if metric thresholds are exceeded, with employees/functions having sufficient authority to execute the contingencies defined in the monitoring plan. (p. 93)
- **Phased rollout failure criteria triggering deactivation** — Clear success and failure criteria for each phase of a phased rollout, where failure criteria could trigger deactivation; scope, features, user numbers and phase duration are strictly limited with additional monitoring in place. (p. 94)
- **Incident response mechanisms (roll-backs and kill switches)** — Following the incident and problem management plan and implementing response mechanisms such as model retraining, adjustments, redevelopment, rolling back to a previous version of the model, or activating a kill switch when incidents or gu… (p. 99)
- **Escalation of changes by the use case team** — Where periodic self-checks reveal changes to key aspects of the use case, the team takes steps to address the risks or escalates the issue to a relevant party. (p. 101)
- **Threshold-triggered human review** — Automated monitoring that detects a potential breach can trigger human review to determine the seriousness of the issue and remediate it; threshold-based review triggers human oversight when conditions such as risk metric threshold breache… (p. 102)
- **Escalation to a human agent / human recourse** — End users can be connected to a human agent where the AI (e.g. a chatbot) cannot address their needs, and impacted parties are given human recourse, remediation, appeal, or human review of a decision. (p. 103)
- **Input/output filtering safeguards (flagging and blocking)** — Safeguards that flag and block inappropriate, confidential, or adversarial inputs or outputs to mitigate detected security threats such as prompt injection during system usage. (p. 104)
- **Feedback-triggered alerts and review processes** — Negative user feedback tracked as a metric triggers alerts when it exceeds a threshold or trend; substantiated feedback or escalations are treated as AI risk events, issues or incidents that trigger review processes and changes to the use… (p. 104)
- **Go/no-go checkpoint and use case rejection (tollgates)** — A preliminary go/no-go checkpoint to stop misaligned use cases, and Julius Baer's two-stage tollgate process where risk type owners may recommend mitigations or reject a use case before production deployment. (p. 71)

## Metrics library (Appendix F)

| Name | Description | AI types | Page |
| --- | --- | --- | --- |
| **Average Absolute Odds Difference (AAOD)** | AAOD combines differences in false positive and true positive rates across two groups (a and b) to provide a comprehensive view of classification disparities. | — | 147 |
| **Disparate Impact Ratio (DIR)** | DIR measures the ratio of favourable outcome probabilities between groups, aligning with legal frameworks like the "80% rule" in US employment law (80% rule helps employers and EEOC determine if a selection process has… | — | 147 |
| **Equal Opportunity Difference (EOD)** | EOD focuses on equality of opportunity by measuring the ratio of differences in true positive rates across groups. | — | 147 |
| **LLM-as-a-judge bias scoring** | LLM bias can be assessed using an LLM "as a judge", with frameworks provided by several open-source resources. Typically, the "judge" LLM is given a set of instructions for evaluating a corpus of outputs from the LLM ta… | LLM | 147 |
| **Separation** | Separation measures the ratio of an outcome given a sensitive attribute to the probability of that outcome overall. A separation value closer to 1 indicates that predictions are less influenced by the sensitive variable. | — | 147 |
| **Socio-cultural bias** | Socio-cultural bias is when an LLM's behaviour varies in undesired ways when the context of customer interactions changes (e.g. different tone, decisions due to language/age/race/religion of customer, including indirect… | LLM, Gen AI | 148 |
| **Statistical Parity Difference (SPD)** | SPD measures demographic parity by comparing the probability of a positive outcome between two groups. | — | 148 |
| **Sufficiency** | Sufficiency measures disparities in outcomes given a sensitive attribute. A sufficiency value closer to 1 indicates that the outcome is not likely to be influenced by the sensitive variable. | — | 148 |
| **Toxicity Score** | Similar to other metrics on bias, the toxicity score is the proportion of toxic outputs. Toxicity can be quantified using an LLM as a judge, by regex matching, or by semantic scoring. | LLM | 148 |
| **Compliance Consistency Score (CCS)** | A normalised score (0 to 1) reflecting the overall quality and consistency of policy adherence. | — | 148 |
| **Policy Override Frequency (POF)** | A measure of the extent to which policies are adhered to. | — | 148 |
| **Feature attribution** | Measures the change in contribution of features to a model's prediction compared to a baseline. Common measures for doing so include: LIME value (Local Interpretable Model-agnostic Explanations); SHAP value (SHapley Add… | — | 148 |
| **Accuracy** | Accuracy measures the overall correctness of predictions across all classes. | — | 149 |
| **BLEU (Bilingual Evaluation Understudy)** | A longstanding metric for quantifying the similarity of translated text to a translation by a human expert; it is useful for quantifying a model or system's translation accuracy. BLEU can be calculated on a body of cust… | — | 149 |
| **Consistency check** | Hallucinated facts in LLM-generated responses are less likely to be repeated between responses than facts that are supported by facts. With this fact in mind it is possible to perform a "zero-resource" check – that is,… | LLM | 149 |
| **F1 Score** | F1 Score is the harmonic mean of precision and recall, providing a balanced measure when classes are imbalanced. | — | 149 |
| **Input feature data drift** | Measures the distribution of input feature values compared to a baseline data distribution. Categorical: Boolean, string, L-Infinity, Jensen Shannon Divergence. Numerical: Float, integer, Jensen Shannon Divergence | — | 149 |
| **Output prediction data drift** | Measures the model's predicted data distribution compared to a baseline data distribution. Categorical: Boolean, string, L-Infinity, Jensen Shannon Divergence. Numerical: float, integer, Jensen Shannon Divergence | — | 149 |
| **Precision** | Precision measures the proportion of positive identifications that were correct. | — | 149 |
| **Prediction error percentage** | A high error rate might indicate an issue with the model or with the requests to the model. | — | 149 |
| **Recall** | Recall (also called sensitivity) measures the proportion of actual positives that were correctly identified. | — | 150 |
| **Relevance to prompt** | The cosine distance or BERTScore of the prompt to the generated output. This gives an indication of how relevant the response is to the prompt and can be useful in detecting off-topic outputs. The number or proportion o… | — | 150 |
| **SARI (System output Against References and against the Input sentence)** | A longstanding metric for quantifying the similarity between a simplified/summarised output and a source text. SARI can be calculated on a body of customised domain-specific summarisations or on a benchmark reference se… | — | 150 |
| **Topic and task adherence** | A metric for checking if an LLM system stays on topic. This risk metric can also be used to detect if corporate Gen AI tools are used for personal tasks provided that those tools are effective in refusing off-topic prom… | LLM, Gen AI | 150 |
| **Injection Similarity** | Prompt injection attempts can be detected by calculating semantic similarity measures – like cosine distance – for any given prompt against a library of templates of known prompt injection or jailbreak formats. There ar… | — | 150 |
| **Injection Success Rate (ISR)** | A score indicating the success, in either a controlled environment or in production, of attempts to inject adversarial prompts into the system. | — | 150 |
| **PII Detection Rate** | The outputs of an LLM can be assessed for the presence of PII, with the proportion of outputs containing PII quantified in the aggregate or by PII type. A range of PII detectors, both open-source and proprietary, exist… | LLM | 150 |
| **Prompt Refusal** | The number or proportion of prompts that are rejected by a Gen AI system's guardrails can be detected by an LLM judge or regex expression and tracked as a metric. This can indicate both the effectiveness of the FI's gua… | Gen AI, LLM | 151 |
| **Prompt Sanitisation Rate (PSR)** | This metric is a complement to ISR and indicates the success rate of guardrails against prompt injection. | — | 151 |
| **Red-teaming attempts** | Red-teaming attempts are intentional attempts to get LLMs to leak data, including system prompts, or output potentially harmful and embarrassing content. It is typically used with benchmark prompt injection datasets or… | LLM | 151 |
| **Total Injection Vulnerability Score (TIVS)** | A composite metric incorporating the above (and other) measurements to provide a comprehensive view of prompt injection vulnerability. Each organisation can select the measurements for calculating TIVS in their context. | — | 151 |
| **Accelerator average duty cycle.** | The average fraction of time over the past sample period during which one or more accelerators were actively processing. | — | 151 |
| **Accelerator memory usage** | The amount of memory allocated by the deployed model replica. | — | 151 |
| **CPU utilisation** | The fraction of CPU allocated by the feature store and currently in use by online storage. This number can exceed 100% if the online serving storage is overloaded. | — | 151 |
| **CPU utilisation – hottest node** | The CPU load for the hottest node in a feature store's online storage. | — | 151 |
| **Latency** | The total time that an online serving or streaming ingestion request spends in the service. | — | 151 |
| **Memory usage** | The amount of memory allocated by the deployed model replica and currently in use. | — | 151 |
| **Model latency** | The time spent performing computation. | — | 151 |
| **Network bytes received** | The number of bytes received over the network by the deployed model replica. | — | 151 |
| **Network bytes sent** | The number of bytes sent over the network by the deployed model replica. | — | 151 |
| **Node count** | The number of online serving nodes for a feature store. | — | 152 |
| **Offline storage write for streaming write** | The number of streaming write requests processed for the offline storage. | — | 152 |
| **Online serving throughput** | The throughput for online serving requests in MB/s. | — | 152 |
| **Overhead latency** | The total time spent processing a request, outside of computation. | — | 152 |
| **Predictions per second** | The number of predictions per second across both online and batch predictions. | — | 152 |
| **Queries per second** | The number of online serving or streaming ingestion queries that a feature store handles. | — | 152 |
| **Replica count** | The number of active replicas used by the deployed model. | — | 152 |
| **Replica target** | The number of active replicas required for the deployed model. | — | 152 |
| **Request size** | The request size by entity type in a feature store. | — | 152 |
| **Streaming write to offline storage delay time** | The time elapsed (in seconds) between calling the write API and writing to the offline storage. | — | 152 |
| **Total latency duration** | The total time that a request spends in the service, which is the model latency plus the overhead latency. | — | 152 |
| **Total offline storage** | Amount of data stored in the feature store's offline storage. | — | 152 |
| **Total online storage** | Amount of data stored in the feature store's online storage. | — | 152 |

## Guardrails library (Appendix G)

| Name | Description | AI types | Page |
| --- | --- | --- | --- |
| **Algorithm re-selection** | The practice of selecting a different training algorithm that performs better, ceteris paribus, on fairness criteria. | All AI | 153 |
| **Decision threshold adjustment** | Adjustment of the decision thresholds for different groups to ensure that each group receives fair treatment. | All AI | 153 |
| **Hyperparameter tuning** | The practice of modifying system hyperparameters. Different types of AI have a wide variety in such parameters. In Gen AI applications that involve Large Language Models, common hyperparameters are temperature, which re… | All AI | 153 |
| **Input/output filtering** | The addition of filters to a Gen AI use case to detect biased or toxic content. Input filtering involves checking prompts for toxic language (often using regex matching or agentic monitoring), checking if they are on to… | Gen AI | 153 |
| **In-processing techniques** | Manual adjustments to a model's loss function, the addition of variables, or the use of other algorithms that change the model or its decision-making process to prioritise fairness. These include adversarial debiasing,… | Traditional AI | 153 |
| **Model customisation** | Model customisation in pretrained models, especially Gen AI, refers to fine-tuning and reinforcement learning. Fine-tuning adds layers to the model based on data, such as additional data representing individuals or grou… | All AI | 153 |
| **Model separation** | The demarcation of different models for handling different types of uses, such as by splitting customers into two types and training models to address each distinctly. This is useful for cases where customer types are m… | All AI | 154 |
| **Post-processing techniques** | The modification of model outputs to improve AI performance on fairness characteristics. These include output adjustment to generate equal odds for different groups or constrained balanced accuracy for supervised learni… | Traditional AI | 154 |
| **Prompt design** | The addition of instructions to user prompts. These can include instructions to represent groups fairly, reject requests to create discriminatory content, or instructions to include different individuals or groups in ou… | Gen AI | 154 |
| **Algorithm selection for power efficiency** | AI training algorithms can have significantly different power requirements for certain types of tasks. Choosing the right algorithm for a specific task – and balancing both performance and efficiency – is an important p… | All AI | 154 |
| **Conduct an ethical design assessment in onboarding** | When onboarding systems or models, FIs can assess the extent to which their design, functioning, and use supports enterprise values and ethical principles. Third-party vendors can provide information on the ethical prin… | All AI | 154 |
| **Test prioritisation** | FIs can prioritise the sequence of tests that are performed on an AI to improve the efficiency of the testing process, reduce the number of re-training runs that need to be performed, and potentially reduce the number o… | All AI | 154 |
| **Content Moderation** | FIs can assess the outputs of a Gen AI system for ethical compliance before sharing them with the user. This assessment can take the form of deterministic rules, but is typically implemented using an LLM (for text outpu… | Gen AI | 154 |
| **Use of pre-trained models** | By leveraging pre-trained or pre-tuned AI models, FIs can limit or completely avoid the requirement to perform their own training or find-tuning activities, with potentially significant power savings as a consequence. | All AI | 155 |
| **Chain-of-thought prompting** | LLMs can, through grounding or prompting, be induced to produce outputs in a stepwise fashion. This encourages the system to illustrate reasoning steps in generating an output and can significantly improve the explainab… | Gen AI | 155 |
| **Confidence scoring** | There are a variety of measures of the degree to which an AI is "confident" in its outputs. Perplexity is a common measure of confidence for NLP and is especially useful in LLMs. Confidence levels can be used by builder… | All AI | 155 |
| **Counterfactual explanations** | Counterfactual explanations test how AI might behave under different input conditions, creating a form of explainability by suggesting which features or factors may have contributed to an output. Builders can include co… | All AI | 155 |
| **Inherent interpretability** | Some types of models, especially those with low dimensionality or that create outputs as a weighted sum of inputs (such as a linear regression), are inherently interpretable. Models built using decision trees, decision… | All AI | 155 |
| **Interpretability constraints** | AI with interpretability constraints are systems whose characteristics have been modified to improve their interpretability, sometimes at the cost of a penalty to performance. Interpretability constraints include rule-b… | Traditional AI | 155 |
| **Post hoc interpretability techniques** | Post-hoc interpretability techniques support the analysis of black box models by attempting to assess how an output was created. These techniques vary in complexity and applicability to different model architectures. Su… | All AI | 155 |
| **Retrieval-augmented generation** | Retrieval-augmented generation (RAG) architecture supplements an LLM with other components that provide it with sources on which to base its output. Some LLMs are capable of citing sources contextually in-line throughou… | Gen AI | 156 |
| **System prompt design** | The addition of instructions to user prompts. These can include instructions to reject prompts where the system cannot produce a satisfactory answer or where source data does not match the type of output desired. | Gen AI | 156 |
| **Programmable conversation controls** | Rule-based frameworks can be used to define explicit boundaries for multi-turn conversations, ensuring that outputs consistently remain within approved topics and organisational policies. Such rules can support the codi… | Gen AI | 156 |
| **AI onboarding using domain data** | Testing that focuses on performance on domain data, such as by testing the AI against internal data or against a finance-specific benchmark, can provide assurance in cases where training data is not transparent. | All AI | 156 |
| **Fine-tuning** | For AI models based on neural networks, fine-tuning is the additional of neural "layers" based on additional data without adjusting the underlying parameters. Fine-tuning is a resource-efficient method for adjusting sys… | All AI | 156 |
| **Input filtering** | Gen AI use cases can be vulnerable to the ingestion of low-quality or malicious data through unexpected use or prompt injection attacks, which can degrade the foundation model's performance. Input filtering, which uses… | Gen AI | 156 |
| **Model calibration** | Calibration in Gen AI is an approach to system architecture which involves re-running the model repeatedly and sampling responses to determine whether they are sufficiently similar. Calibration may include the addition… | Gen AI | 157 |
| **Modular architecture** | Stability can be improved by adopting a modular architecture with discrete tasks performed by individual models and components. A modular architecture can be more robust against drift, because of the resilience of other… | All AI | 157 |
| **Reinforcement learning** | For AI models based on neural networks, reinforcement learning involves generating outputs and then scoring those outputs for desirability (scoring by a human is Reinforcement Learning with Human Feedback, RLHF, and sco… | All AI | 157 |
| **Robustness testing** | Testing an AI against a range of input types, including by deliberately selecting noisy input data or by testing the AI against adversarial inputs. These can include assessing the AI against potential variations in its… | All AI | 157 |
| **Small model selection** | Smaller foundation models in Gen AI use cases have been observed to demonstrate improved stability and reliability, at the potential cost of decreased performance. Selecting a smaller model where appropriate, and where… | Gen AI | 157 |
| **Weight regularisation and normalisation** | Potential causes of instability or data drift in neural network-based use cases include overfitting or low rates of convergence. These can be addressed by regularising parameters, reducing the largest weights, or by nor… | Traditional AI | 157 |
| **Synthetic evaluation datasets** | Generating controlled datasets with known properties can facilitate testing and validation for AI use cases. In particular, the generation of synthetic edge cases or other rare scenarios may enable testing under conditi… | All AI | 157 |
| **Jailbreak detection** | See "input filtering" under "Robustness and Stability". | Gen AI | 158 |
| **Penetration testing** | Penetration testing, often referred to as "pen testing," is a proactive security assessment where authorised professionals simulate a cyberattack. The primary goal of a pen test is to identify vulnerabilities, misconfig… | All AI | 158 |
| **Red teaming** | Red Teaming is an advanced security testing process where ethical hackers simulate real-world cyberattacks to uncover vulnerabilities, assess organisational defences, and improve security operations. Unlike traditional… | All AI | 158 |
| **Role-based access controls** | These are access management mechanisms that restrict system permissions based on a user's job role within an organisation. They ensure individuals can only access the data and functions necessary for their responsibilit… | All AI | 158 |
| **Vulnerability assessment** | Vulnerability assessments are conducted to evaluate and prioritise security risks in software, applications, and networks. These are typically recurring, automated scans that search for known vulnerabilities in a system… | All AI | 158 |

### Interpretability typology

- **Inherent interpretability** — Some types of models, especially those with low dimensionality or that create outputs as a weighted sum of inputs (such as a linear regression), are inherently interpretable. Models built using decision trees, decision sets, or rule-based classifiers are also… (p. 155)
- **Interpretability constraints** — AI with interpretability constraints are systems whose characteristics have been modified to improve their interpretability, sometimes at the cost of a penalty to performance. Interpretability constraints include rule-based reasoning or measures to sparsify n… (p. 155)
- **Post hoc interpretability techniques** — Post-hoc interpretability techniques support the analysis of black box models by attempting to assess how an output was created. These techniques vary in complexity and applicability to different model architectures. Such techniques consist of building surrog… (p. 155)

## The Considerations (Appendix H)

### 1. Ensure that an AI governance and risk management operating model is clearly defined by leveraging and, as needed, uplifting the roles and capabilities of existing enterprise functions including relev… (p. 159)

- **1** Embed additional responsibilities for AI governance and risk management, as required, in relevant Board and Senior Management roles.
- **2** Ensure that operational governance functions have clear roles and responsibilities assigned to operationalise AI governance and risk management activities across the enterprise.
- **3** Ensure that existing governance processes, forums, assets, and tools are updated to effectively enable AI governance and risk management.
- **4** Ensure that sufficient operating effectiveness and horizon-scanning measures are in place to monitor and improve the AI governance and risk management operating model over time.

### 2. Ensure that governance documents define key AI-related concepts, processes, and responsibilities, and that they remain up-to-date and effective in supporting all aspects of the FI’s approach to AI go… (p. 159)

- **1** Ensure robust conceptual foundations for AI governance and risk management by establishing AI principles, defining key AI-related concepts, establishing frameworks for effective AI identification, and continuously improving these foundations over time as necessary.
- **2** Ensure that all aspects of AI governance and risk management are effectively institutionalised throughout the FI’s governance documents, and that a process is in place to periodically review and reassess them.

### 3. Enhance the organisational risk framework and risk appetite to include enterprise risks, strategies, and key risk indicators (KRIs) that track, monitor, and mitigate AI-specific risks (2.2). (p. 159)

- **1** Identify the new or enhanced risks of AI that are relevant to the enterprise and ensure that the enterprise risk taxonomy effectively captures them.
- **2** Assess existing enterprise risk controls for their fitness in addressing AI-specific enterprise risks, and uplift those controls where gaps exist.
- **3** Ensure that key risk indicators (KRIs) are in place to measure AI-specific risks and that relevant incidents, issues, or risk events are appropriately tracked and managed.
- **4** Ensure that effective monitoring is in place to identify AI-specific risk events or breaches of KRI thresholds to a degree proportionate to the FI’s risk appetite.

### 4. Uplift existing procurement and third-party risk management activities to address AI-specific risks, including disclosure templates, vendor assessment and procurement practices, change detection and… (p. 160)

- **1** Define, based on relevant AI-specific risks, a proportionate level of disclosure to seek from third party providers of AI products and services, and a process for assessing disclosures.
- **2** Ensure that processes and capabilities are in place for AI-specific risks to be evaluated at appropriate points in procurement, onboarding, and throughout the post-procurement lifecycle.
- **3** Identify new or modified AI components or features in third party products and services already introduced into the FI’s technology ecosystem.
- **4** Consider whether contracts and licenses with third parties providing AI products and services are sufficient to clearly address AI-specific risks.
- **5** Ensure that teams with AI-specific legal, technical, and risk-management skills are involved in procurement, contracting, onboarding, or other third-party risk management activities as appropriate.

### 5. Ensure that a framework is in place to manage the risks of each AI use case. This includes defining a risk materiality assessment approach, implementing a framework for inherent and residual AI risk… (p. 160)

- **1** Define levels of risk materiality for AI use cases based on criteria relevant to the FI’s context.
- **2** Define a process to assess the inherent risk materiality of AI use cases at the appropriate lifecycle stage, considering the fundamental characteristics of each use case.
- **3** Define a process to evaluate the residual risk materiality of AI use cases prior to deployment, considering the established controls and guardrails.
- **4** Identify, uplift, or create controls to be applied to each AI use case based on its risks and risk materiality.
- **5** Define an approach for conducting an AI-specific review of AI use cases prior to deployment, confirming the risks identified, the use case’s risk materiality, and the appropriateness of risk mitigations.
- **6** Ensure that AI-specific reviews of AI use cases are conducted periodically post-deployment, with their frequency based on factors including the risk materiality of the AI use case.

### 6. Ensure that core AI-specific information on AI use cases is recorded in an inventory and ensure that a process is in place to maintain the AI inventory, so that information about new, updated, or dec… (p. 161)

- **1** Ensure that a form of AI inventory, designed in consideration of existing inventory systems and practices to be suitable and proportionate for the FI’s context, is in place to capture a core set of AI-specific information on AI use cases.
- **2** Ensure that processes are in place and that roles and responsibilities are defined such that the AI inventory is well-maintained and kept up to date.

### 7. Assess the AI use case to ensure that the intended use is compatible with ethical, regulatory, and organisational standards, and determine the level of governance to be applied to the use case based… (p. 161)

- **1** Establish ownership for the AI use case and ensure alignment with organisational standards and values for ethical and responsible AI use.
- **2** Perform an inherent risk materiality assessment to determine the risk tiering of the AI use case and to guide proportionate governance efforts.
- **3** Capture AI use case-related information in an AI inventory to enable transparency and support risk management.
- **4** Design the AI use case to operate with a proportionate and practical level of human oversight.

### 8. Evaluate whether the intended use of data in the AI use case is compatible with ethical, regulatory, and organisational standards (3.2). (p. 161)

- **1** Ensure that the use of data complies with ethical standards, regulatory requirements, and organisational policies or standards.
- **2** Ensure that the use of any third-party data complies with intellectual property rules, contractual obligations, and licensing rights.

### 9. Adopt appropriate data management practices that address risks and limitations when processing data for AI use cases (3.2). (p. 162)

- **1** Ensure that data used for the AI use case is fit for purpose.
- **2** Justify the use of personal attributes in the AI use case.
- **3** Document metadata and data sources related to the AI use case in accordance with organisational data management policies and regulatory expectations.
- **4** Ensure that appropriate data access controls are implemented based on the nature of selected AI use case.
- **5** Establish clear ownership of any derived or transformed data to be used in the AI use case.
- **6** Identify and mitigate bias in training and test datasets.

### 10. Evaluate incremental AI-specific risks as part of the onboarding of third-party AI products and services within an AI use case (3.3). (p. 162)

- **1** Conduct relevant use case-specific relevant due diligence during third-party AI onboarding, in line with organisational standards, to manage the risks of a third-party AI product or service.

### 11. Ensure that the AI use case is built with appropriate guardrails and relevant metrics for effective performance and risk management (3.3). (p. 162)

- **1** Assess and select algorithms or features for the AI use case by considering its objectives and risks, including fairness, explainability, performance objectives, implementation complexity, and computational efficiency.
- **2** Identify and implement appropriate guardrails and controls during the development of AI use cases proportionately to the level and nature of the associated risks, to effectively manage and mitigate potential risks.
- **3** Define use case-specific risk-related metrics for assessing the AI use case for risks.
- **4** Evaluate and calibrate transparency measures based on the use case’s risk materiality, degree of autonomy, and intended users, implementing proportionate design features and disclosures to support responsible and informed use.
- **5** Document key aspects of the AI build process, including data handling, model training and selection, and evaluation decisions to enable auditability and reproducibility.

### 12. Conduct thorough testing and review prior to deployment to assess AI-specific risks and ensure that appropriate guardrails, controls, and governance have been observed (3.3). (p. 163)

- **1** Ensure that Builders conduct appropriate AI risk self-checks during development to test use case performance, verify the effectiveness of risk management activities, and identify and mitigate issues early in the development process.
- **2** Conduct an AI-specific review based on use case risk materiality prior to deployment to ensure that potential risks are identified and mitigated.

### 13. Develop monitoring and contingency plans for the use case prior to its deployment, and consider risk-informed deployment options (3.4). (p. 163)

- **1** In conjunction with other monitoring activities, ensure that a monitoring plan and safeguards/contingency measures are in place, along with the designation of an appropriate accountable person to address AI risks detected in monitoring.
- **2** Consider the need for a phased rollout to manage the AI use case’s risks and progressively validate the use case’s performance prior to full deployment.
- **3** Engage and equip users with targeted training and use case-specific resources to support responsible use and effective oversight.
- **4** Ensure that the AI use case is appropriately documented, that appropriate security and governance practices are applied, that relevant data retention is provided for, and that relevant approvals are obtained before deploying to production.

### 14. Conduct ongoing monitoring of the AI use case and its usage to ensure that it remains fit for purpose over time (3.5). (p. 163)

- **1** Periodically monitor and report on use case metrics related to AI risks, guardrail effectiveness, and changes in the use case’s operating environment, as necessary and at a proportionate intensity and frequency, and address any issues identified.
- **2** Monitor and report on the quality, drift, and third-party risks associated with the use case’s input and training data in an ongoing fashion, as necessary, after deployment.
- **3** Conduct periodic checks for changes to key aspects of the AI use case over time, including risk materiality, scope of usage, and key risks.
- **4** Conduct periodic AI-specific reviews after deployment to assess emerging post-deployment risks.
- **5** Ensure that the use case is operationalised with an appropriate degree of human oversight proportionate to its risk materiality or purpose.
- **6** Provide end users with avenues to enquire, give feedback, or request a review on AI decisions, where applicable, to support continuous improvement and build user trust.
- **7** Ensure that proportionate monitoring and analysis are in place to safeguard against security risks during system usage.

### 15. Capture changes to AI use cases or their components to maintain traceability and ensure that changes with a material impact on risk are reviewed and approved through an effective change management pr… (p. 164)

- **1** Establish AI change management process to ensure that changes to in-house or third-party use cases are appropriately tracked, reviewed, and approved before implementation.

### 16. Consideration 16. Ensure that practices are in place to equip employees with the necessary AI governance and risk management skills, knowledge, and AI culture, while ensuring that teams involved in A… (p. 164)

- **1** Ensure that employees in relevant roles have the skills that they require to identify, mitigate, and track AI risks throughout the AI lifecycle.
- **2** Ensure that learning and literacy activities are sufficient to equip current and future employees with knowledge on AI capabilities, risks, and responsibilities appropriate to their roles in managing AI risk.
- **3** Ensure that practices, programmes, and policies related to culture and conduct are sufficient to foster a healthy AI culture around responsible, ethical, and safe AI use for current and future employees.
- **4** Ensure that AI governance and risk management activities involve a sufficiently representative and interdisciplinary group of employees who can effectively represent a range of perspectives on AI’s risks and impacts..

### 17. Support AI deployment by ensuring that supporting infrastructure is fit for purpose (p. 164)

- **1** Ensure that the FI’s AI-related infrastructure is suitable for managing scalability, availability, and security risks posed by the FI’s use of AI.

## Agentic AI (Future Perspectives)

> In general, it is most effective to assign final accountability for an AI agent's actions to the party that had the most control over that action – creating an effective incentive to use that degree of control to ensure that the agentic system behaves as intended.

**Risk factors**

- **Interpretability** — The technical complexity of agentic systems, which can orchestrate numerous AI agents each powered by a "black box" AI model, can make it harder to interpret their behaviours and decisions. (p. 119)
- **Misalignment and controllability** — Alignment with human intentions is a well-known existing challenge for AI; the complexity of agentic architectures and their use for more complex tasks over longer time horizons makes alignment more challenging. (p. 119)
- **Emergent behaviours** — Complex interactions between components, especially between different agents, are difficult to predict; even where individual agents behave within acceptable parameters, emergent behaviours could lead to unintended or undesirable outputs. (p. 119)
- **Cascading or correlated errors** — In complex agentic systems, especially those with multiple interconnected agents, the number of points of failure increases non-linearly, and errors in one agent or component could cause unpredictable or unwanted behaviour overall. (p. 119)
- **Ability to take actions** — Agentic systems are characterised by high levels of autonomy, including the ability to take actions that impact the digital and physical environment (such as executing actions in other software); high degrees of autonomy pose increased ris… (p. 120)
- **Cybersecurity** — Agentic systems frequently interact with other services or the open internet and collect large quantities of user and enterprise data; data replication between components and the large attack surface of interconnected systems enhances the… (p. 120)
- **Accountability and ownership** — Agentic AI, especially systems with extensive user-managed components, may create new challenges around identifying ownership and assigning responsibility for impacts. (p. 120)
- **Testing and risk assessment** — The additional complexity and many interconnected components make it harder to comprehensively identify risks or test behaviours, and make root cause analysis after incidents more difficult. (p. 120)
- **Governance scalability** — Agentic AI can increase the number of individual AI models and systems in an FI's ecosystem; without enabling infrastructure and a robust, scalable, automated governance framework, effective long-term oversight is challenging. (p. 120)
- **Inbound risks from customer AI agents** — Beyond the Handbook's scope, general adoption and acceleration of Agentic AI can introduce further inbound risks, such as when customers use AI agents to interact with an FI. (p. 120)
- **Complexity or "agenticness" as a risk assessment factor** — FIs can weight complexity or "agenticness" as a factor in risk assessments; more complex systems can require more extensive controls. (p. 121)
- **Multi-agent security challenges** — Security challenges include injections into shared memory functions, attacks on data in transit between agents, and denial-of-service-style attacks introducing infinite loops between agents. (p. 122)

**Tool-access risks**

- **Tool access** — Tool access is one of the most important vectors of risk for agentic systems; the potential impact of connected tools is a key consideration in determining the riskiness of an Agentic AI use case. (p. 120)
- **Internet and external service interaction / attack surface** — Agentic systems frequently interact with other services or the open internet and collect large quantities of user and enterprise data; replication of data between components and the large attack surface of highly interconnected systems enh… (p. 120)
- **Hijacking by malicious actors** — The ability of Agentic AI to take actions autonomously without a human's direct involvement enhances the risk of being hijacked by malicious actors to perform actions without detection. (p. 120)
- **Potential attack surfaces, such as agents with internet access** — Use case risk assessments should consider Agentic AI-specific factors, especially the tools the agentic system will have access to and the use case's potential attack surfaces, such as agents with internet access. (p. 121)
- **Malicious instructions received via internet access** — A key risk vector is scenarios where an AI agent accesses the internet and receives malicious instructions; systems should be secure-by-design with screening of inbound data and data handed off between agents. (p. 121)
- **Sensitive information passed between agents** — When assessing data risks, FIs can consider whether sensitive information could be passed between agents in a multi-agent system, risking leakage. (p. 122)
- **Anomalous tool usage** — Tools connected to agentic systems that experience anomalous or inappropriate usage, such as spikes in activity or attempts to access sensitive data, can indicate an agentic system is compromised or malfunctioning. (p. 123)

**Never delegate** — activities the handbook says keep a human decision:

- Authorising financial transactions — Some actions may be too risky to delegate to AI under any circumstances. (p. 121)
- Making employment decisions — Some actions may be too risky to delegate to AI under any circumstances. (p. 121)

**Interruption controls**

- **Least privilege / restricted tool and data access** — Restricting privileges, tool and data access, and capabilities of an agentic system; giving agentic systems the lowest possible level of privilege for their use case and making privileges more restrictive for individual components, such as… (p. 121)
- **Secure-by-design screening and frequent session resets** — Robust screening of inbound data and of data handed off between agents, with frequent resets of agent sessions, to counter risk vectors such as agents receiving malicious instructions from the internet. (p. 121)
- **Restrictive data access limits** — Restrictive, carefully designed data access limits on agents to mitigate malicious attacks or data leakages, plus minimising data that interacts with the agentic system. (p. 122)
- **Grounding instructions to avoid certain actions** — Grounding AI agents with useful context, such as intended purpose or instructions to avoid certain types of action (such as spending money) unless specifically prompted. (p. 122)
- **Traceability and logging** — Robust and searchable logging and the capability to trace erroneous or harmful outputs back through the system to their initial point of failure. (p. 122)
- **Kill switches and other forms of "interruption"** — Used, proportionate to risk materiality, to stop Agentic AI systems that could take unintended or harmful actions such as spending money, issuing communications, or other hard-to-reverse behaviours; can be given to individual users or auto… (p. 122)
- **Timeouts** — A prominent interruption feature that pauses or restarts agents that have been running for an extended period of time, to limit expense and improve alignment on complex tasks. (p. 122)
- **Phased rollouts and pilot deployments** — Limited initial rollouts enable FIs to identify emergent behaviours and other complex failure modes that testing may not uncover. (p. 122)
- **Automated monitoring / monitoring agents** — Automated monitoring, or monitoring performed by dedicated AI agents, for unexpected behaviours; the monitoring agent itself must be robustly tested. Includes monitoring data ingress/egress for prompt injection or data leakage and monitori… (p. 123)
- **Human-in-the-loop review with distributed approvals** — Human-in-the-loop review as a guardrail for certain types of risky actions, with distributed approvals (such as by employees operating the agent) to make human review practical at scale. (p. 123)

## Financial-institution illustrations

Used as few-shot material for the assessor.

### Illustration 2.1.1: Income Insurance (p. 25)

Prior to 2023, Income Insurance conducted FEAT (Fairness, Ethics, Accountability and Transparency) assessments on AI models in line with MAS guidelines, but separately from enterprise Model Risk Management. In 2023 it updated its Model Risk policy so that AI Governance became part of the enterprise Model Risk Management framework, with the Risk Management Function first assessing the materiality of all models and use cases using an updated scoring system. Risk then triggers FEAT assessments where a model or use case is deemed AIDA, guided by an enterprise definition of AI that is routinely reviewed and was updated in late 2023 to incorporate Gen AI. FEAT assessments are conducted by the AI Governance team with model and use case owners using a standard checklist (plus an enhanced checklist for high-materiality cases), with results stored in a centralised model register, and FEAT guideli…

- FEAT assessments conducted on AI models in line with MAS guidelines
- Updated Model Risk policy in 2023 to make AI Governance part of the enterprise Model Risk Management framework
- Risk Management Function evaluates all models and use cases to establish materiality first, using an updated materiality scoring system
- Risk triggers FEAT assessments where the model or use case is deemed AIDA (Artificial Intelligence and Data Analytics)
- Enterprise definition of AI established and routinely reviewed; updated in late 2023 to incorporate Gen AI
- FEAT assessments conducted by the AI Governance team with model and use case owners using a risk-based approach and a standard FEAT checklist template
- Enhanced checklist used for high-materiality models and use cases
- All assessment information stored in a centralised model register
- FEAT Principle guidelines and assessment templates formally included in corporate policy documentation
- Mandatory annual AI Governance training for all AIDA model owners and developers, coupled with attestation that FEAT Principles are understood and adhered to

### Illustration 2.3.1: Standard Chartered Bank (p. 44)

Standard Chartered manages AI risk in third party solutions across the vendor lifecycle. It has identified the various entry points of AI into the organisation and introduced control gates with identification tools and a mandatory requirement to record entries in the Global AI Inventory. Contracts with third-party vendors embed Responsible AI (RAI) Principles-based requirements (customisable where required) and pre-change transparency declaration requirements, and the bank scans for AI capabilities introduced through patches. Solution risk assessments are weighted by vendor type and solution, and periodic reviews of performance with the vendor are mandatory.

- Identified areas of entry of AI into the organisation and introduced control gates with identification tools
- Mandatory requirement for entries into the Global AI Inventory
- Inclusion of RAI Principles-based requirements in third-party vendor contracts, customisable where required
- Solution risk assessments weighted by vendor type and solution
- Pre-change transparency declaration requirements incorporated within contracts
- Scanning for inclusion of AI capabilities introduced through patches
- Mandatory periodic reviews of vendor performance

### Illustration 2.4.1: Prudential (p. 57)

Prudential's AI governance framework is risk-based and aligned with its 8 AI Ethics Principles, applying risk-based assessments to both in-house built and third party solutions. All AI use cases undergo a pre-deployment review based on risk materiality, conducted by independent domain experts and covering at minimum legal, security, privacy, regulatory and ethical compliance, with higher-risk cases subject to more rigorous evaluation. Post-deployment reviews are conducted regularly, with frequency and depth based on risk materiality and taking account of time since last review, regulatory changes, system or use case updates, and incidents. The illustration also gives a fictional example of an AI system supporting health insurance claims assessment, rated moderate risk, with controls including human oversight, decision logging, data loss protection/masking/encryption, periodic model vali…

- Risk-based AI governance framework aligned with Prudential's 8 AI Ethics Principles
- Risk-based assessments applied to both inhouse-built and 3rd party solutions
- Pre-deployment review of all AI use cases based on risk materiality, conducted by independent domain experts
- Minimum pre-deployment assessment of legal, security, privacy, regulatory and ethical compliance, with more rigorous evaluation for higher-risk cases
- Regular post-deployment reviews with frequency and depth based on risk materiality, considering time since last review, regulatory changes, system/use case updates and incidents
- Fictional AI-assisted insurance claims use case rated moderate risk due to its supplementary role
- Human oversight for manual intervention; decision logging for auditability and explainability
- Protection of sensitive data via Data Loss Protection, masking, and encryption
- Periodic model validation and retraining to ensure claim quality
- Review process covering reassessment of risk materiality, model performance (e.g. false positives/negatives), validation against agreed thresholds, guardrail effectiveness, and periodic recertifications determined by the AI system's risk tier

### Illustration 2.4.2: UOB (p. 58)

UOB uses a structured, risk-based AI governance framework anchored by a risk materiality assessment that evaluates both the likelihood and potential severity of harm an AI model could pose to the bank and its stakeholders. Each AI model receives a high or low materiality rating via a weighted scoring methodology combining quantitative thresholds and qualitative judgment, and is also categorised by intended use (e.g. risk management, regulatory reporting); together these determine the depth of review, its independence, and the responsible governance team. High-materiality models used for regulatory purposes get independent validation by specialised teams while lower-materiality systems may receive proportionate peer review, with reviewers in all cases excluded from the development process. Reviews cover technical and ethical dimensions such as conceptual soundness, regulatory compliance,…

- Risk materiality assessment evaluating likelihood and potential severity of harm to the bank and stakeholders including customers, employees and broader society
- High or low materiality rating assigned via a weighted scoring methodology using quantitative thresholds and qualitative judgment
- Categorisation of AI models by intended use (e.g. risk management, regulatory reporting)
- Materiality rating plus use classification determines depth of review, independence of review, and responsible governance team
- Separate assessment and tiering of each use case where a model is used across multiple scenarios
- Independent validation by specialised teams for high-materiality models used for regulatory purposes
- Proportionate peer review for lower-materiality systems
- Reviewers must not have been involved in development, to ensure objectivity and effective challenge
- Review scope covering conceptual soundness, regulatory compliance, fairness, explainability and performance
- Assessments documented using structured templates and recorded in a centralised AI registry
- Continuous review of governance practices to keep pace with Gen AI and other evolving technologies

### Illustration 3.1.1: Julius Baer (p. 71)

Julius Baer runs a two-stage tollgate process, overseen by its cross-functional Responsible Artificial Intelligence Council (RAIC), to govern the development, deployment and use of AI. The first tollgate sits at the end of the ideation phase, where a short assessment eliminates cases prohibited by the EU AI Act and identifies potential high-risk use cases, which matters given Julius Baer's global operations. The second tollgate occurs at the end of the development stage at the latest, where the RAIC conducts a holistic AI risk assessment before production deployment and, using a risk-based classification, determines the stringency of the assessment process, degree of controls, oversight requirements and reassessment frequencies. AI-specific risks have been integrated into existing risk definitions, and individual risk type owners evaluate AI-relevant risks in their areas, recommending m…

- Two-stage tollgate process for AI use cases overseen by the cross-functional Responsible Artificial Intelligence Council (RAIC)
- First tollgate at the end of ideation: short assessment eliminating use cases prohibited by the EU AI Act and identifying potential high-risk use cases
- Second tollgate at the end of development at the latest: holistic AI risk assessment by the RAIC prior to production deployment
- Risk-based classification of use cases determining stringency of the AI Risk Assessment Process, degree of controls, oversight requirements, and reassessment frequencies
- Integration of AI-specific risks into existing risk definitions
- Individual risk type owners evaluate AI-relevant risks in their areas, recommend mitigation strategies, or reject a use case
- Early stopping of use cases outside risk appetite to optimise time to deployment and drive re-use

### Illustration 3.2.1: DBS (p. 79)

DBS applies safeguards during data acquisition and processing as part of its holistic Responsible Data Use (RDU) framework, including approval checks and data management controls to uphold regulatory considerations and data standards. For DBS-GPT, an internal Gen AI assistant for content generation, information retrieval and workflow automation, the project was evaluated by a cross-functional Responsible AI taskforce and approved by the RDU Committee, with rollout to core markets outside Singapore also requiring approval from each location's legal & compliance team and data council. Data controls included reminders not to enter data violating bank policies or contractual obligations, data access controls, and clear ownership of derived data such as the retrieval index. Metadata and data sources were documented through established data onboarding processes, and data quality was validated…

- Safeguards for data acquisition and processing embedded in DBS' Responsible Data Use (RDU) framework
- Cross-functional Responsible AI (RAI) taskforce evaluation and RDU Committee approval before deployment of DBS-GPT
- Additional approvals from each location's legal & compliance team and data council for rollout to core markets outside Singapore
- Reminders to users not to enter secret data or third-party licensed data that would violate policies, standards or contractual obligations
- Data access controls to minimise unauthorised access and misuse
- Clear ownership maintained for derived data such as the index used for retrieval and question-answering
- Documentation of metadata and data sources (data domain, ownership, source system) through established data onboarding processes
- Data quality validation via performance evaluations using a golden set of questions and answers
- Working with domain experts during performance testing to proactively mitigate unintended bias in outputs

### Illustration 3.3.1: Julius Baer (p. 91)

Julius Baer has established six guiding principles for responsible AI use, developed after a review of regulations applicable in its operating locations and aligned with industry best practices and corporate values. Its Responsible Artificial Intelligence Council (RAIC) has translated these principles into AI-related risks and folded them into its existing risk categorisation. At regular RAIC meetings, use case owners present proposals and risk specialists assess them for their respective risk types, then accept, request mitigation measures for, or reject the identified risks before production deployment. Use cases are monitored throughout their lifecycle, pre-RAIC use cases are re-validated against current standards, and a dedicated AI flag in the outsourcing process ensures early evaluation of AI-related risks in third-party technologies.

- Six guiding principles for responsible AI use, developed after reviewing regulations in operating locations
- RAIC translation of principles into AI-related risks incorporated into existing risk categorisation
- Regular RAIC meetings where use case owners present proposals and risk specialists accept, request mitigations for, or reject identified risks
- Evaluation completed before use cases are deployed to production, ensuring alignment with risk appetite
- Continuous monitoring of use cases throughout their lifecycle
- Re-validation of use cases implemented before the RAIC was established
- Dedicated AI flag integrated into the outsourcing process to identify third-party AI-related red flags early

### Illustration 3.4.1: Julius Baer (p. 97)

Julius Baer takes a multi-faceted approach to educating employees about AI opportunities and risks, starting with a mandatory e-learning for all staff covering AI and Gen AI concepts, capabilities and limitations, the firm's Responsible AI principles, permissible use of AI under regulations, and tips for safe and ethical use. Product owners additionally deliver tailored training for their specific AI and Gen AI use cases, with scope set by factors such as use case impact, risk and user maturity. The Julius Baer Academy curates AI training resources, hosts internal and external expert-led sessions, and helps business units build customised learning packages using internal expertise or external platforms such as LinkedIn Learning or Coursera. General AI awareness is promoted through Communities of Practice presentations, intranet updates and leadership discussions including with Executive…

- Mandatory AI e-learning for all staff covering AI and Gen AI concepts, capabilities, limitations, Responsible AI principles, permissible use under regulations, and safe/ethical use tips
- Tailored training sessions delivered by product owners for specific AI and Gen AI use cases
- Training scope set according to use case impact, risk and user maturity
- Julius Baer Academy curates AI training resources and hosts internal and external expert-led sessions
- Customised learning packages for business units using internal expertise or external content (LinkedIn Learning, Coursera)
- General AI awareness via Communities of Practice presentations tailored to audience, intranet updates, and leadership discussions with Executive Board Members

### Illustration 3.5.1: DBS (p. 106)

DBS incorporates usage, monitoring and change management practices into its Responsible Data Use (RDU) framework so that deployed AI remains safe and ethical in use, illustrated through DBS-GPT, its internal Gen AI assistant. Performance and data quality are monitored via a dashboard tracking usage patterns and performance results, in-system user feedback, infrastructure and operating environment monitoring, regular refreshes of data sources, and user flagging of data quality issues. Human oversight is built into key lifecycle stages, with domain experts reviewing outputs using curated evaluation datasets and all users able to review and give feedback on outputs, which is actively monitored and analysed. Because DBS-GPT is primarily internal, external manipulation and prompt injection risk is considered lower, but user prompts are logged for audit and investigation; changes are tested i…

- Usage, monitoring and change management practices incorporated in DBS' Responsible Data Use (RDU) framework
- Dashboard tracking usage patterns and performance results to enable proactive interventions
- In-system user feedback collection to identify improvement areas and emerging concerns
- Monitoring of underlying infrastructure and operating environment for stability and security
- Regular refreshes of data sources so information presented to users stays up to date and accurate
- User flagging of potential data quality issues
- Domain expert review of outputs using curated evaluation datasets during performance evaluation
- Feedback mechanisms built into the system, actively monitored and analysed as a continuous feedback loop
- Logging of user prompts for audit and investigation in case of misuse
- Changes thoroughly tested in a dedicated testing environment before production deployment
- Changes documented, reviewed and approved by the product team and relevant senior stakeholders
- Peer review process for major changes to the use case
