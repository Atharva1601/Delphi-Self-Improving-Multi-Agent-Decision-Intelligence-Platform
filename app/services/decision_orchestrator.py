"""
app/services/decision_orchestrator.py
───────────────────────────────────────
Master pipeline controller for the Delphi decision engine.
Runs the full pipeline and updates Case status at every step.

Pipeline:
  PENDING → ROUTING → COUNCIL_FORMATION → DEBATE → JUDGING → CONSENSUS → COMPLETED
  (Any step failure → FAILED)
"""
import asyncio
import json

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from app.consensus import service as consensus_svc
from app.consensus.schemas import ConsensusOutput
from app.council import service as council_svc
from app.database.session import AsyncSessionLocal
from app.debate import service as debate_svc
from app.domain import service as domain_svc
from app.judge import service as judge_svc
from app.models.case import Case, CaseStatus, CaseVerdict
from app.reputation.service import (
    process_reputation_updates,
    calculate_simulated_reputation_updates,
)
from app.router import service as router_svc


def get_mock_data(query: str) -> dict:
    q_lower = query.lower()
    if any(k in q_lower for k in ["diagnostics", "hospital", "medical", "clinical"]):
        return {
            "routing": {
                "industry": "Healthcare & Medicine",
                "domains": ["AI Safety", "Medical Ethics", "Clinical Operations", "Healthcare IT"]
            },
            "domain_context": {
                "key_assumptions": [
                    "AI model accuracy exceeds 95% in clinical trials.",
                    "EHR integration APIs are available and standardized.",
                    "Medical staff will undergo training on AI decision boundaries."
                ]
            },
            "council_members": [
                "Technical Architect Expert",
                "Legal Expert",
                "Operations Expert",
                "Product Strategy Expert"
            ],
            "selection_reasoning": (
                "Selected Technical Architect Expert for EHR API feasibility; "
                "Legal Expert for malpractice and HIPAA compliance liability; "
                "Operations Expert for clinical workflow and alert fatigue risk; "
                "Product Strategy Expert for clinician trust and explainability."
            ),
            "debate": {
                "round1_analyses": [
                    {
                        "expert_name": "Technical Architect Expert",
                        "reasoning": "Deploying the diagnostic model on-premise inside a secure HIPAA-compliant VPC ensures sub-100ms inference times. Standard HL7/FHIR APIs will link predictions directly into the existing EHR flow, with an automatic fallback to manual triage if latency exceeds 500ms."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "reasoning": "AI diagnosis introduces malpractice exposure. To protect the hospital, the AI must act strictly as a passive second-opinion tool. The final diagnosis must be explicitly signed off by a human doctor, and the AI's role must be fully disclosed to patients."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "reasoning": "ER triage is a high-stress, fast-paced environment. Introducing another screen or click will lead to workflow bypass. Furthermore, if the AI generates too many low-risk alerts, it will cause severe alert fatigue, leading clinicians to ignore true positive warnings."
                    },
                    {
                        "expert_name": "Product Strategy Expert",
                        "reasoning": "Adoption depends entirely on explainability. A raw probability score (e.g., '85% risk') will be ignored or distrusted. The UI must highlight the specific clinical parameters or imaging regions that drove the model's warning so doctors can verify it instantly."
                    }
                ],
                "round2_challenges": [
                    {
                        "expert_name": "Operations Expert",
                        "challenge": "Operations Expert, how will you mitigate the alert fatigue that typically leads ER staff to mute critical diagnostic warning systems?",
                        "targeted_assumption": "AI alerts will be integrated cleanly."
                    },
                    {
                        "expert_name": "Technical Architect Expert",
                        "challenge": "Technical Architect Expert, how do we guarantee patient data privacy and zero leak risks during peak real-time inference hours?",
                        "targeted_assumption": "EHR integration APIs are secure."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "challenge": "Legal Expert, how does our malpractice liability shift if a physician overrides an AI recommendation that later turns out to be correct?",
                        "targeted_assumption": "AI must act as second opinion."
                    }
                ],
                "round3_rebuttals": [
                    {
                        "expert_name": "Operations Expert",
                        "rebuttal": "We will implement an 'Alert Severity Threshold' so only high-risk discrepancies trigger pop-up warnings. Low-risk warnings will be silently logged. We will also cap alerts to a maximum of 10% of total triaged cases during the pilot phase."
                    },
                    {
                        "expert_name": "Technical Architect Expert",
                        "rebuttal": "No patient-identifiable data (PII) will leave our secure firewall. We will strip names and IDs at the gateway level, passing only anonymized clinical metrics to the inference engine, with full end-to-end TLS encryption."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "rebuttal": "Overriding AI is standard medical discretion. As long as we implement mandatory logging where the doctor selects a quick reason for override (e.g., 'clinical counter-evidence'), we preserve our standard of care protections in court."
                    }
                ]
            },
            "judge_rubric": {
                "expert_scores": [
                    {
                        "expert_name": "Technical Architect Expert",
                        "evidence_score": 8.5,
                        "logic_score": 9.0,
                        "consistency_score": 8.8,
                        "rebuttal_quality": 8.5,
                        "overall_score": 8.7,
                        "feedback": "Strong architecture plan with solid security safeguards and standard integrations."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "evidence_score": 8.8,
                        "logic_score": 8.5,
                        "consistency_score": 8.7,
                        "rebuttal_quality": 8.8,
                        "overall_score": 8.7,
                        "feedback": "Clear boundaries defined for liability, though override logs must be strictly enforced."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "evidence_score": 8.2,
                        "logic_score": 8.9,
                        "consistency_score": 8.4,
                        "rebuttal_quality": 8.7,
                        "overall_score": 8.5,
                        "feedback": "Excellent focus on ER stress constraints. The alert rate cap is a very practical solution."
                    },
                    {
                        "expert_name": "Product Strategy Expert",
                        "evidence_score": 8.4,
                        "logic_score": 8.6,
                        "consistency_score": 8.5,
                        "rebuttal_quality": 8.0,
                        "overall_score": 8.4,
                        "feedback": "Explainability is a great insight, but requires more engineering detail."
                    }
                ],
                "avg_evidence_quality": 8.5,
                "avg_logic_score": 8.8,
                "avg_consistency_score": 8.6,
                "avg_rebuttal_quality": 8.5,
                "overall_quality_score": 8.6,
                "strongest_argument": "Operations Expert's warning that ER staff will bypass a high-friction UI is the most critical constraint.",
                "weakest_argument": "Product Strategy Expert's explainability focus is vital for trust, but lacks precise system design details."
            },
            "consensus": {
                "verdict": "conditional_approve",
                "confidence": 88.0,
                "executive_summary": (
                    "# Executive Summary: AI-Assisted ER Diagnostics\n\n"
                    "### Recommendation\n**CONDITIONAL APPROVAL** (88% Confidence)\n\n"
                    "### Key Conditions\n"
                    "1. **Human-in-the-Loop**: The AI system must act *only* as a decision-support aid. A licensed physician must make and sign off on all final diagnoses.\n"
                    "2. **Zero-Latency Fallback**: The EHR integration must default to normal manual triage within 500ms if the AI server fails to respond.\n"
                    "3. **Alert Fatigue Cap**: Limit alerts to cases where the AI's confidence differs significantly from the triage nurse's score, capped at 10% of cases."
                )
            }
        }
    elif any(k in q_lower for k in ["southeast", "asia", "expand", "market", "expansion"]):
        return {
            "routing": {
                "industry": "Business Expansion & Global Markets",
                "domains": ["Market Strategy", "Finance", "Regulatory Compliance", "Product Strategy"]
            },
            "domain_context": {
                "key_assumptions": [
                    "Target market has high smartphone adoption rates.",
                    "Local entity establishment takes 6-9 months.",
                    "Existing local competitors have deep distribution networks."
                ]
            },
            "council_members": [
                "Business Market Expert",
                "Finance Expert",
                "Legal Expert",
                "Product Strategy Expert"
            ],
            "selection_reasoning": (
                "Selected Business Market Expert for competitive landscape and localized fit; "
                "Finance Expert for NPV and runway implications; "
                "Legal Expert for entity setup and local compliance; "
                "Product Strategy Expert for localization and mobile experience."
            ),
            "debate": {
                "round1_analyses": [
                    {
                        "expert_name": "Business Market Expert",
                        "reasoning": "Southeast Asia has high growth potential, but local giants (Grab, GoTo) dominate. We should target a B2B SaaS niche first, serving regional mid-market enterprises rather than competing for mass consumer acquisition."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "reasoning": "Expanding immediately requires $1.8M in capital, cutting our runway from 18 months to 10 months. Given current currency volatility, we must secure a localized credit line or bridge round before proceeding."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "reasoning": "Establishing corporate entities in Indonesia and Vietnam takes at least 6 months. Additionally, local data privacy rules (like PDPA in Singapore and Indonesia's PDP law) require localized databases, which increases hosting costs."
                    },
                    {
                        "expert_name": "Product Strategy Expert",
                        "reasoning": "Over 90% of local internet users are mobile-only. Our web portal is too heavy. We must redesign a lightweight mobile web portal and integrate local payment gateways (e.g. GoPay, OVO, ShopeePay)."
                    }
                ],
                "round2_challenges": [
                    {
                        "expert_name": "Business Market Expert",
                        "challenge": "Business Market Expert, how will we compete against established local players with deep localization and capital?",
                        "targeted_assumption": "Target market has high growth potential."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "challenge": "Finance Expert, is the projected customer lifetime value (LTV) high enough to justify cutting our runway in half?",
                        "targeted_assumption": "Runway will drop from 18 to 10 months."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "challenge": "Legal Expert, what is the timeline and cost for establishing legal entities in Vietnam and Indonesia?",
                        "targeted_assumption": "Establishing entities takes 6 months."
                    }
                ],
                "round3_rebuttals": [
                    {
                        "expert_name": "Business Market Expert",
                        "rebuttal": "We will partner with local regional distributors and focus purely on premium enterprise clients where local consumer-focused giants are weak."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "rebuttal": "By using a phased roll-out starting with Singapore, we can limit initial CapEx to $500k, preserving a 15-month runway while testing product-market fit."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "rebuttal": "We can use an Employer of Record (EoR) model initially to hire local sales staff without establishing full legal entities, reducing setup time from 9 months to 4 weeks."
                    }
                ]
            },
            "judge_rubric": {
                "expert_scores": [
                    {
                        "expert_name": "Business Market Expert",
                        "evidence_score": 8.2,
                        "logic_score": 8.5,
                        "consistency_score": 8.0,
                        "rebuttal_quality": 8.7,
                        "overall_score": 8.3,
                        "feedback": "Strong advice on targeting B2B SaaS niche to avoid direct consumer battles."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "evidence_score": 8.5,
                        "logic_score": 8.7,
                        "consistency_score": 8.6,
                        "rebuttal_quality": 8.4,
                        "overall_score": 8.5,
                        "feedback": "Prudent runway conservation strategy; Singapore pilot is highly sensible."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "evidence_score": 8.0,
                        "logic_score": 8.4,
                        "consistency_score": 8.2,
                        "rebuttal_quality": 8.5,
                        "overall_score": 8.2,
                        "feedback": "Using an Employer of Record (EoR) is a brilliant shortcut to test the market."
                    },
                    {
                        "expert_name": "Product Strategy Expert",
                        "evidence_score": 8.4,
                        "logic_score": 8.3,
                        "consistency_score": 8.1,
                        "rebuttal_quality": 8.0,
                        "overall_score": 8.2,
                        "feedback": "Mobile UX points are critical, but implementation details are still high-level."
                    }
                ],
                "avg_evidence_quality": 8.2,
                "avg_logic_score": 8.5,
                "avg_consistency_score": 8.2,
                "avg_rebuttal_quality": 8.4,
                "overall_quality_score": 8.3,
                "strongest_argument": "Finance Expert's warnings about cutting the company runway in half is the most critical immediate constraint.",
                "weakest_argument": "Product Strategy Expert's mobile-first transition details need practical software architecture definitions."
            },
            "consensus": {
                "verdict": "conditional_approve",
                "confidence": 82.0,
                "executive_summary": (
                    "# Executive Summary: Southeast Asian Market Expansion\n\n"
                    "### Recommendation\n**CONDITIONAL APPROVAL** (82% Confidence)\n\n"
                    "### Key Conditions\n"
                    "1. **Phased Roll-out**: Launch in Singapore first to validate enterprise demand before expanding to Indonesia or Vietnam.\n"
                    "2. **Employer of Record**: Avoid high legal setup costs by hiring local sales and support staff via an EoR for the first 12 months.\n"
                    "3. **Mobile-First Localization**: Re-engineer the client portal to support regional e-wallets and optimize for mobile web."
                )
            }
        }
    elif any(k in q_lower for k in ["autonomous", "banking", "bank", "digital banking", "global"]):
        return {
            "routing": {
                "industry": "Financial Technology & Global Banking",
                "domains": ["Finance", "Legal", "Security", "Technical", "Operations", "Product Strategy", "Business"]
            },
            "domain_context": {
                "key_assumptions": [
                    "AI banking platforms meet strict global financial regulations.",
                    "High-volume real-time transaction database maintains zero downtime.",
                    "Fraud detection models achieve sub-50ms inference times."
                ]
            },
            "council_members": [
                "Finance Expert",
                "Legal Expert",
                "Security Expert",
                "Technical Architect Expert",
                "Operations Expert",
                "Product Strategy Expert",
                "Business Market Expert"
            ],
            "selection_reasoning": (
                "Selected all 7 Delphi experts to address the complex regulatory, financial, "
                "security, architecture, operational, and product strategy requirements."
            ),
            "debate": {
                "round1_analyses": [
                    {"expert_name": "Finance Expert", "reasoning": "Launching globally requires a reserve of $25M for regulatory capital. The projected ROI is 35% starting in Year 3, assuming customer acquisition cost remains under $15."},
                    {"expert_name": "Legal Expert", "reasoning": "Autonomous banking faces strict regulatory barriers. We must obtain licenses in each region individually and comply with anti-money laundering (AML) laws."},
                    {"expert_name": "Security Expert", "reasoning": "AI banking platforms are prime targets. We must implement zero-trust network access, end-to-end encryption, and a 24/7 security operations center."},
                    {"expert_name": "Technical Architect Expert", "reasoning": "Our core banking ledger must support 10,000 transactions per second. We should deploy a multi-region distributed SQL database with active-active replication."},
                    {"expert_name": "Operations Expert", "reasoning": "Customer disputes require instant automated handling. We will integrate an LLM-powered agent support desk, with human escorts for complex cases."},
                    {"expert_name": "Product Strategy Expert", "reasoning": "User acquisition depends on seamless onboarding. We must design a lightweight mobile app integrating one-click KYC and digital wallets."},
                    {"expert_name": "Business Market Expert", "reasoning": "Fintech giants (Revolut, Wise) dominate the consumer market. We should target unbanked segments in emerging markets to establish early footholds."}
                ],
                "round2_challenges": [
                    {"expert_name": "Finance Expert", "challenge": "Finance Expert, how will you mitigate risk if regional capital requirements double during the launch phase?", "targeted_assumption": "Regulatory capital remains at $25M."},
                    {"expert_name": "Legal Expert", "challenge": "Legal Expert, how do we address cross-border data residency requirements for global users?", "targeted_assumption": "Global data can be processed centrally."},
                    {"expert_name": "Security Expert", "challenge": "Security Expert, how will the fraud detection system handle high-volume DDoS attacks during peak hours?", "targeted_assumption": "Fraud detection scales cleanly."},
                    {"expert_name": "Technical Architect Expert", "challenge": "Technical Architect Expert, how do we prevent transactional conflicts during database replication lags?", "targeted_assumption": "Distributed SQL ensures absolute consistency."},
                    {"expert_name": "Operations Expert", "challenge": "Operations Expert, what is the fallback plan if the LLM customer desk hallucinates or leaks private info?", "targeted_assumption": "AI customer support is secure."},
                    {"expert_name": "Product Strategy Expert", "challenge": "Product Strategy Expert, how do we ensure accessibility for non-tech-savvy users in target demographics?", "targeted_assumption": "Mobile app is easy to use."},
                    {"expert_name": "Business Market Expert", "challenge": "Business Market Expert, how will we defend our margins when local competitors launch copycat platforms?", "targeted_assumption": "We can dominate the segment."}
                ],
                "round3_rebuttals": [
                    {"expert_name": "Finance Expert", "rebuttal": "We will secure a $10M backup line of credit and phase our launch, beginning with lower-capital jurisdictions to minimize capital locks."},
                    {"expert_name": "Legal Expert", "rebuttal": "We will deploy local cloud regions (e.g. AWS Local Zones) in high-regulatory areas to keep user data strictly within national borders."},
                    {"expert_name": "Security Expert", "rebuttal": "We will implement Cloudflare Magic Transit to scrub DDoS traffic before it reaches our fraud detection APIs, keeping traffic latency under 10ms."},
                    {"expert_name": "Technical Architect Expert", "rebuttal": "We will enforce serializable transaction isolation on the database, accepting a 5% throughput trade-off to guarantee zero conflicts."},
                    {"expert_name": "Operations Expert", "rebuttal": "All AI customer desk prompts will run inside strict sandbox environments, and queries containing account numbers will be auto-routed to human specialists."},
                    {"expert_name": "Product Strategy Expert", "rebuttal": "We will support voice-guided onboarding and partner with local agents to provide physical cash-in / cash-out kiosks."},
                    {"expert_name": "Business Market Expert", "rebuttal": "We will build a proprietary credit scoring model based on local mobile utility data, creating a defensible data moat."}
                ]
            },
            "judge_rubric": {
                "expert_scores": [
                    {"expert_name": "Finance Expert", "evidence_score": 8.5, "logic_score": 8.8, "consistency_score": 8.5, "rebuttal_quality": 8.6, "overall_score": 8.6, "feedback": "Capital phase-in plan is prudent and significantly limits early budget risk."},
                    {"expert_name": "Legal Expert", "evidence_score": 8.6, "logic_score": 8.5, "consistency_score": 8.7, "rebuttal_quality": 8.8, "overall_score": 8.65, "feedback": "Local data storage strategy cleanly addresses regional sovereignty constraints."},
                    {"expert_name": "Security Expert", "evidence_score": 8.9, "logic_score": 9.1, "consistency_score": 8.8, "rebuttal_quality": 9.0, "overall_score": 8.95, "feedback": "Transit scrubbing is a highly robust solution for fraud API security during surges."},
                    {"expert_name": "Technical Architect Expert", "evidence_score": 8.8, "logic_score": 8.7, "consistency_score": 8.6, "rebuttal_quality": 8.8, "overall_score": 8.725, "feedback": "Serializable database constraints are essential, even with minor speed trade-offs."},
                    {"expert_name": "Operations Expert", "evidence_score": 8.4, "logic_score": 8.8, "consistency_score": 8.5, "rebuttal_quality": 8.7, "overall_score": 8.6, "feedback": "Sandboxed AI support routing protects privacy while maintaining operational efficiency."},
                    {"expert_name": "Product Strategy Expert", "evidence_score": 8.5, "logic_score": 8.4, "consistency_score": 8.3, "rebuttal_quality": 8.5, "overall_score": 8.425, "feedback": "Voice guides and offline kiosks are practical solutions for local user adoption."},
                    {"expert_name": "Business Market Expert", "evidence_score": 8.3, "logic_score": 8.6, "consistency_score": 8.4, "rebuttal_quality": 8.5, "overall_score": 8.45, "feedback": "Utility data moat provides sound strategic differentiation against local copycats."}
                ],
                "avg_evidence_quality": 8.6,
                "avg_logic_score": 8.7,
                "avg_consistency_score": 8.5,
                "avg_rebuttal_quality": 8.7,
                "overall_quality_score": 8.6,
                "strongest_argument": "Security Expert's Cloudflare transit isolation plan provides massive security resilience.",
                "weakest_argument": "Business Market Expert's utility credit scoring assumes local data access remains open."
            },
            "consensus": {
                "verdict": "conditional_approve",
                "confidence": 88.0,
                "executive_summary": (
                    "# Executive Summary: Global AI Banking Platform\n\n"
                    "### Recommendation\n**CONDITIONAL APPROVAL** (88% Confidence)\n\n"
                    "### Core Conditions\n"
                    "1. **Phased Jurisdiction Capitalization**: Start operations in regional hubs with lower reserve mandates to test financial stability.\n"
                    "2. **Data Residency Compliance**: Ensure local user database isolation to meet cross-border sovereignty compliance.\n"
                    "3. **Serializable Isolation**: Force database consistency locks on banking ledgers to prevent transaction conflicts."
                )
            }
        }
    elif any(k in q_lower for k in ["security", "cyber", "cybersecurity", "infrastructure"]):
        return {
            "routing": {
                "industry": "Cybersecurity & Corporate IT",
                "domains": ["Security", "Finance", "Operations", "Technical Architect"]
            },
            "domain_context": {
                "key_assumptions": [
                    "Current firewalls and VPN have active vulnerabilities.",
                    "Upgrades will require database maintenance windows.",
                    "MFA and zero-trust policies will affect employee sign-on times."
                ]
            },
            "council_members": [
                "Security Expert",
                "Finance Expert",
                "Operations Expert",
                "Technical Architect Expert"
            ],
            "selection_reasoning": (
                "Selected Security Expert for threats and zero-trust posture; "
                "Finance Expert for insurance premiums and CapEx ROI; "
                "Operations Expert for employee friction and MFA adoption; "
                "Technical Architect Expert for migration risk and database backups."
            ),
            "debate": {
                "round1_analyses": [
                    {
                        "expert_name": "Security Expert",
                        "reasoning": "Our current firewalls and legacy VPN are vulnerable. A zero-trust network access (ZTNA) model will reduce breach likelihood by 70%, protecting critical IP."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "reasoning": "A $2M investment represents 15% of our annual budget. We must evaluate if this reduces cyber insurance premiums enough to offset the capital expense."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "reasoning": "Strict security rules often lead employees to bypass systems. We must ensure the new identity providers support single-sign-on (SSO) with biometric authentication."
                    },
                    {
                        "expert_name": "Technical Architect Expert",
                        "reasoning": "Migrating our core databases to the new encrypted clusters will require scheduled maintenance. We must ensure legacy APIs are retrofitted first to prevent downtime."
                    }
                ],
                "round2_challenges": [
                    {
                        "expert_name": "The Judge",
                        "challenge": "Security Expert, can we achieve 80% of the security posture improvement with only 50% of the budget ($1M)?",
                        "targeted_expert": "Security Expert"
                    },
                    {
                        "expert_name": "The Judge",
                        "challenge": "Operations Expert, how will we train non-technical departments on the new access control policies?",
                        "targeted_expert": "Operations Expert"
                    },
                    {
                        "expert_name": "The Judge",
                        "challenge": "Technical Architect Expert, what is the risk of database corruption or data loss during the migration?",
                        "targeted_expert": "Technical Architect Expert"
                    }
                ],
                "round3_rebuttals": [
                    {
                        "expert_name": "Security Expert",
                        "rebuttal": "A $1M budget would cover endpoint protection but leaves database access unencrypted. However, we could defer the database encryption phase to Q4."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "rebuttal": "We will roll out mandatory 15-minute interactive video training and run a 2-week pilot with the marketing and sales teams before full enforcement."
                    },
                    {
                        "expert_name": "Technical Architect Expert",
                        "rebuttal": "We will run a parallel staging migration and perform dry runs. A roll-back plan is in place with snapshot recovery points."
                    }
                ]
            },
            "judge_rubric": {
                "expert_scores": [
                    {
                        "expert_name": "Security Expert",
                        "evidence_score": 9.1,
                        "logic_score": 8.8,
                        "consistency_score": 8.9,
                        "rebuttal_quality": 8.8,
                        "overall_score": 8.9,
                        "feedback": "Strong justification for zero-trust, with acceptable flexibility on phasing the rollout."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "evidence_score": 8.5,
                        "logic_score": 8.7,
                        "consistency_score": 8.5,
                        "rebuttal_quality": 8.4,
                        "overall_score": 8.5,
                        "feedback": "Validated that cyber insurance premium discounts will offset about 20% of the annual cost."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "evidence_score": 8.6,
                        "logic_score": 8.9,
                        "consistency_score": 8.7,
                        "rebuttal_quality": 8.8,
                        "overall_score": 8.7,
                        "feedback": "The 2-week pilot and biometric SSO integrations are highly effective adoption mitigations."
                    },
                    {
                        "expert_name": "Technical Architect Expert",
                        "evidence_score": 8.8,
                        "logic_score": 8.6,
                        "consistency_score": 8.5,
                        "rebuttal_quality": 8.9,
                        "overall_score": 8.7,
                        "feedback": "Parallel database migration mitigates critical server downtime effectively."
                    }
                ],
                "avg_evidence_quality": 8.8,
                "avg_logic_score": 8.7,
                "avg_consistency_score": 8.6,
                "avg_rebuttal_quality": 8.7,
                "overall_quality_score": 8.7,
                "strongest_argument": "Security Expert's zero-trust plan provides massive vulnerability mitigation for our core intellectual property.",
                "weakest_argument": "Finance Expert's ROI calculation relies heavily on insurance premium discounts which are not yet fully locked."
            },
            "consensus": {
                "verdict": "approve",
                "confidence": 91.0,
                "executive_summary": (
                    "# Executive Summary: $2M Cybersecurity Infrastructure Upgrade\n\n"
                    "### Recommendation\n**APPROVED** (91% Confidence)\n\n"
                    "### Key Action Items\n"
                    "1. **Phased Budgeting**: Allocate $1.2M immediately to critical ZTNA and endpoint security, reserving $800k for database encryption in Q4.\n"
                    "2. **Training & Pilot**: Run a 2-week user trial with selected business units to ensure smooth adoption of ZTNA.\n"
                    "3. **Parallel Migration**: Maintain full redundant systems during database upgrades to prevent production downtime."
                )
            }
        }
    else:
        return {
            "routing": {
                "industry": "Strategic Business Planning",
                "domains": ["Product Strategy", "Finance", "Legal", "Operations"]
            },
            "domain_context": {
                "key_assumptions": [
                    "The proposal is feasible within current technology stacks.",
                    "Initial capital expenditure is within acceptable thresholds.",
                    "Compliance and legal reviews will be completed prior to launch."
                ]
            },
            "council_members": [
                "Product Strategy Expert",
                "Finance Expert",
                "Legal Expert",
                "Operations Expert"
            ],
            "selection_reasoning": (
                "Selected Product Strategy Expert for customer-facing alignment; "
                "Finance Expert for cost-benefit projections; "
                "Legal Expert for compliance and regulatory checks; "
                "Operations Expert for process execution constraints."
            ),
            "debate": {
                "round1_analyses": [
                    {
                        "expert_name": "Product Strategy Expert",
                        "reasoning": f"Regarding '{query}', this is a highly strategic opportunity. It aligns with long-term product trends, though we must focus on simplicity for the end user."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "reasoning": f"Financially, implementing this query requires significant initial capital. We must analyze the break-even timeline and ROI bounds before allocating budget."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "reasoning": f"We must carefully navigate local and international compliance rules before acting on '{query}'. A thorough risk audit is required."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "reasoning": f"Executing this plan requires coordination across product, engineering, and sales. We need solid standard operating procedures."
                    }
                ],
                "round2_challenges": [
                    {
                        "expert_name": "Product Strategy Expert",
                        "challenge": "Product Strategy Expert, what are the primary competitive risks of executing this plan?",
                        "targeted_assumption": "The proposal is feasible within technology stacks."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "challenge": "Finance Expert, what is the worst-case financial scenario if adoption is slower than expected?",
                        "targeted_assumption": "Initial capital expenditure is within acceptable thresholds."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "challenge": "Legal Expert, how will you address potential compliance audits in the near term?",
                        "targeted_assumption": "Compliance reviews will be completed prior to launch."
                    }
                ],
                "round3_rebuttals": [
                    {
                        "expert_name": "Product Strategy Expert",
                        "rebuttal": "We will mitigate competitive risks by establishing a unique value proposition and moving quickly to capture early users."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "rebuttal": "We will hedge our financial risks by structuring the investment in smaller, milestone-based tranches."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "rebuttal": "We will engage external compliance auditors early in the process to guarantee alignment with all standard frameworks."
                    }
                ]
            },
            "judge_rubric": {
                "expert_scores": [
                    {
                        "expert_name": "Product Strategy Expert",
                        "evidence_score": 8.0,
                        "logic_score": 8.2,
                        "consistency_score": 8.0,
                        "rebuttal_quality": 8.1,
                        "overall_score": 8.1,
                        "feedback": "Sound strategic reasoning with a good focus on user adoption."
                    },
                    {
                        "expert_name": "Finance Expert",
                        "evidence_score": 7.9,
                        "logic_score": 8.4,
                        "consistency_score": 8.1,
                        "rebuttal_quality": 8.0,
                        "overall_score": 8.1,
                        "feedback": "Milestone-based funding is a prudent approach to limit downside risks."
                    },
                    {
                        "expert_name": "Legal Expert",
                        "evidence_score": 8.1,
                        "logic_score": 8.0,
                        "consistency_score": 8.2,
                        "rebuttal_quality": 8.3,
                        "overall_score": 8.15,
                        "feedback": "Audit compliance steps are solid, although standard compliance is straightforward."
                    },
                    {
                        "expert_name": "Operations Expert",
                        "evidence_score": 8.0,
                        "logic_score": 8.1,
                        "consistency_score": 7.8,
                        "rebuttal_quality": 8.2,
                        "overall_score": 8.0,
                        "feedback": "Execution protocols are reasonable, but need more staff capacity detail."
                    }
                ],
                "avg_evidence_quality": 8.0,
                "avg_logic_score": 8.2,
                "avg_consistency_score": 8.0,
                "avg_rebuttal_quality": 8.15,
                "overall_quality_score": 8.1,
                "strongest_argument": "Product Strategy Expert's focus on user-centered simplicity is the most compelling aspect of this plan.",
                "weakest_argument": "Operations Expert's staff allocation numbers require further operational depth."
            },
            "consensus": {
                "verdict": "conditional_approve",
                "confidence": 80.0,
                "executive_summary": (
                    f"# Executive Summary: Strategic Analysis of '{query}'\n\n"
                    "### Recommendation\n**CONDITIONAL APPROVAL** (80% Confidence)\n\n"
                    "### Summary of Findings\n"
                    "The council evaluated the strategic proposal and reached a consensus of conditional approval. The primary benefits include market alignment and growth potential, balanced against financial outlays and operational complexity. Implementing standard compliance protocols and milestone-based funding is highly recommended."
                )
            }
        }


async def run_simulated_pipeline(
    case_id: str,
    query: str,
    debate: bool = True,
    reflection: bool = True,
) -> None:
    logger.info(f"Running simulated pipeline — case_id={case_id} debate={debate} reflection={reflection}")
    mock_data = get_mock_data(query)
    accumulated = {}

    try:
        # ── Step 1: Routing ────────────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.ROUTING)
        await asyncio.sleep(0.5 if not debate else 1.0)

        accumulated["routing"] = mock_data["routing"]
        accumulated["domain_context"] = mock_data["domain_context"]
        await _update_stage(case_id, accumulated)

        # ── Step 2: Council Formation ──────────────────────────────────────────
        await _update_status(case_id, CaseStatus.COUNCIL_FORMATION)
        await _update_status(
            case_id,
            CaseStatus.COUNCIL_FORMATION,
            council_members=json.dumps(mock_data["council_members"]),
        )
        accumulated["council_members"] = mock_data["council_members"]
        accumulated["selection_reasoning"] = mock_data["selection_reasoning"]
        await _update_stage(case_id, accumulated)
        await asyncio.sleep(0.5 if not debate else 1.0)

        # ── Step 3: Debate ─────────────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.DEBATE)
        if debate:
            accumulated["debate"] = mock_data["debate"]
            await _update_stage(case_id, accumulated)
            await asyncio.sleep(1.5)
        else:
            accumulated["debate"] = {
                "round1_analyses": mock_data["debate"]["round1_analyses"],
                "round2_challenges": [],
                "round3_rebuttals": [],
            }
            await _update_stage(case_id, accumulated)
            await asyncio.sleep(0.5)

        # ── Step 4: Judging ────────────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.JUDGING)
        judge_rubric = mock_data["judge_rubric"]
        if not debate:
            adjusted_scores = []
            for score in judge_rubric["expert_scores"]:
                adj_score = score.copy()
                adj_score["rebuttal_quality"] = score["logic_score"]
                adj_score["overall_score"] = round(
                    (score["evidence_score"] + score["logic_score"] + score["consistency_score"] + score["logic_score"]) / 4,
                    2
                )
                adjusted_scores.append(adj_score)
            judge_rubric = judge_rubric.copy()
            judge_rubric["expert_scores"] = adjusted_scores

        accumulated["judge_rubric"] = judge_rubric
        await _update_stage(case_id, accumulated)
        await asyncio.sleep(0.5)

        # ── Step 5: Consensus ──────────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.CONSENSUS)
        await asyncio.sleep(0.2)

        # ── Step 6: Completed ──────────────────────────────────────────────────
        verdict_map = {
            "approve": CaseVerdict.APPROVE,
            "reject": CaseVerdict.REJECT,
            "conditional_approve": CaseVerdict.CONDITIONAL_APPROVE,
        }
        consensus = mock_data["consensus"]
        debate_data = accumulated["debate"]

        simulated_reputation_updates = await calculate_simulated_reputation_updates(
            analyses=debate_data["round1_analyses"],
            rebuttals=debate_data.get("round3_rebuttals", []),
            expert_scores=judge_rubric["expert_scores"],
            strongest_argument=judge_rubric["strongest_argument"],
            weakest_argument=judge_rubric["weakest_argument"],
            case_id=case_id,
        )

        # Simulate reflections & success patterns in demo/mock mode
        sim_reflections = []
        sim_patterns = []
        if reflection:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    from sqlalchemy import select
                    from app.models.expert import Expert
                    from app.models.reflection import Reflection
                    from app.models.success_pattern import SuccessPattern

                    expert_names = [u["expert_name"] for u in simulated_reputation_updates]
                    stmt = select(Expert).where(Expert.name.in_(expert_names))
                    res = await session.execute(stmt)
                    db_experts = {e.name.lower(): e for e in res.scalars().all()}

                    for u in simulated_reputation_updates:
                        score = u["contribution_score"]
                        name = u["expert_name"]
                        expert = db_experts.get(name.lower())
                        if not expert:
                            continue

                        if score < settings.reflection_failure_threshold:
                             reflection_obj = Reflection(
                                 expert_id=expert.id,
                                 case_id=case_id,
                                 failure_type="generic_analysis",
                                 lesson=(
                                     f"The expert failed to address specific domain constraints "
                                     f"effectively for query '{query[:80]}'. "
                                     f"Provide highly detailed evidence next time."
                                 ),
                             )
                             session.add(reflection_obj)
                             sim_reflections.append({
                                 "expert_name": name,
                                 "failure_type": "generic_analysis",
                                 "lesson": reflection_obj.lesson,
                             })
                        elif score > settings.reflection_success_threshold:
                             pattern_obj = SuccessPattern(
                                 expert_id=expert.id,
                                 case_id=case_id,
                                 success_pattern=(
                                     f"Demonstrated exceptional structural analysis and logical "
                                     f"consistency when evaluating query '{query[:80]}'."
                                 ),
                             )
                             session.add(pattern_obj)
                             sim_patterns.append({
                                 "expert_name": name,
                                 "success_pattern": pattern_obj.success_pattern,
                             })

        full_result = {
            **accumulated,
            "consensus": consensus,
            "reputation_updates": simulated_reputation_updates,
            "reflections": sim_reflections,
            "success_patterns": sim_patterns,
        }

        await _update_status(
            case_id,
            CaseStatus.COMPLETED,
            verdict=verdict_map.get(consensus["verdict"], CaseVerdict.INCONCLUSIVE),
            confidence=consensus["confidence"],
            executive_report=consensus["executive_summary"],
            raw_result=json.dumps(full_result),
        )
        await _update_stage(case_id, full_result)

        logger.info(f"Simulated pipeline complete — case_id={case_id}")

    except Exception as exc:
        logger.exception(f"Simulated pipeline failed — case_id={case_id}: {exc}")
        await _update_status(
            case_id,
            CaseStatus.FAILED,
            error_detail=str(exc),
        )


async def _update_status(case_id: str, status: CaseStatus, **kwargs) -> None:
    """Update case status (and optional fields) in a fresh DB session."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            case = await session.get(Case, case_id)
            if case:
                case.status = status
                for k, v in kwargs.items():
                    setattr(case, k, v)
            else:
                logger.error(f"Failed to update status to {status.value}: case {case_id} not found in database")


async def _update_stage(case_id: str, stage_data: dict) -> None:
    """Persist an incremental stage snapshot for live UI polling."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            case = await session.get(Case, case_id)
            if case:
                case.stage_data = json.dumps(stage_data)
            else:
                logger.error(f"Failed to update stage data: case {case_id} not found in database")


async def run(
    case_id: str,
    query: str,
    mock: bool = False,
    debate: bool = True,
    reflection: bool = True,
) -> None:
    """
    Execute the full Delphi decision pipeline for a case.
    This function is called as a FastAPI BackgroundTask — it manages its
    own DB sessions since BackgroundTask runs after the request session closes.
    """
    if mock:
        await run_simulated_pipeline(case_id, query, debate=debate, reflection=reflection)
        return

    logger.info(f"Pipeline starting — case_id={case_id} debate={debate} reflection={reflection}")

    # Accumulate stage data incrementally so each snapshot builds on the last
    accumulated: dict = {}

    try:
        # ── Step 1: Route the query ────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.ROUTING)
        routing = await router_svc.route_query(query)

        accumulated["routing"] = routing.model_dump()

        # ── Step 2: Domain context ─────────────────────────────────────────────
        domain_context = await domain_svc.get_domain_context(query, routing)

        accumulated["domain_context"] = domain_context.model_dump()

        # ── Step 3: Council formation ──────────────────────────────────────────
        await _update_status(case_id, CaseStatus.COUNCIL_FORMATION)
        async with AsyncSessionLocal() as session:
            council, selection_reasoning = await council_svc.build_council(
                query, routing, domain_context, session
            )
            council_names = [e.name for e in council]
            expert_ids = [e.id for e in council]

        accumulated["council_members"] = council_names
        accumulated["selection_reasoning"] = selection_reasoning

        await _update_status(
            case_id,
            CaseStatus.COUNCIL_FORMATION,
            council_members=json.dumps(council_names),
        )
        await _update_stage(case_id, accumulated)

        # Need to reload experts in a fresh session for the debate
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            from app.models.expert import Expert
            result = await session.execute(
                select(Expert).where(Expert.id.in_(expert_ids))
            )
            council_experts = list(result.scalars().all())

            # Retrieve past domain lessons and check recovery status
            from app.reflection.service import get_domain_lessons, is_expert_in_recovery
            expert_lessons = {}
            recovery_status = {}
            for e in council_experts:
                in_recovery = await is_expert_in_recovery(session, e.id)
                recovery_status[e.id] = in_recovery
                
                if reflection:
                    # Fetch up to 5 failure reflections if expert is in recovery
                    limit = 5 if in_recovery else 3
                    reflections, success_patterns = await get_domain_lessons(
                        session=session,
                        domain=e.domain,
                        limit=limit
                    )
                    expert_lessons[e.id] = (reflections, success_patterns)
                else:
                    expert_lessons[e.id] = ([], [])

        # ── Step 4: Debate (3 rounds) ──────────────────────────────────────────
        await _update_status(case_id, CaseStatus.DEBATE)
        debate_result = await debate_svc.run_debate(
            query,
            domain_context,
            council_experts,
            expert_lessons=expert_lessons,
            recovery_status=recovery_status,
            debate=debate,
        )

        accumulated["debate"] = {
            "round1_analyses": [a.model_dump() for a in debate_result.round1_analyses],
            "round2_challenges": [c.model_dump() for c in debate_result.round2_challenges],
            "round3_rebuttals": [r.model_dump() for r in debate_result.round3_rebuttals],
        }
        await _update_stage(case_id, accumulated)

        # ── Step 5: Judge evaluation ───────────────────────────────────────────
        await _update_status(case_id, CaseStatus.JUDGING)
        rubric = await judge_svc.evaluate_debate(debate_result, debate_enabled=debate)

        accumulated["judge_rubric"] = rubric.model_dump()
        await _update_stage(case_id, accumulated)

        # ── Step 6: Consensus ──────────────────────────────────────────────────
        await _update_status(case_id, CaseStatus.CONSENSUS)
        consensus = await consensus_svc.form_consensus(query, debate_result, rubric)

        # ── Step 7: Persist result ─────────────────────────────────────────────
        verdict_map = {
            "approve": CaseVerdict.APPROVE,
            "reject": CaseVerdict.REJECT,
            "conditional_approve": CaseVerdict.CONDITIONAL_APPROVE,
        }
        # Update expert reputations, participations, and history
        reputation_updates = await process_reputation_updates(
            case_id=case_id,
            analyses=debate_result.round1_analyses,
            rebuttals=debate_result.round3_rebuttals,
            expert_scores=rubric.expert_scores,
            strongest_argument=rubric.strongest_argument,
            weakest_argument=rubric.weakest_argument,
            consensus_verdict=consensus.verdict,
        )

        # Run reflection engine (Clerk)
        clerk_data = {"reflections": [], "success_patterns": []}
        if reflection:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    from app.reflection.service import run_reflection_engine
                    clerk_data = await run_reflection_engine(
                        case_id=case_id,
                        query=query,
                        debate_result=debate_result,
                        rubric=rubric,
                        reputation_updates=reputation_updates,
                        session=session,
                    )

        full_result = {
            **accumulated,
            "consensus": consensus.model_dump(),
            "reputation_updates": reputation_updates,
            "reflections": clerk_data.get("reflections", []),
            "success_patterns": clerk_data.get("success_patterns", []),
        }

        await _update_status(
            case_id,
            CaseStatus.COMPLETED,
            verdict=verdict_map.get(consensus.verdict, CaseVerdict.INCONCLUSIVE),
            confidence=consensus.confidence,
            executive_report=consensus.executive_summary,
            raw_result=json.dumps(full_result),
        )
        await _update_stage(case_id, full_result)

        logger.info(
            f"Pipeline complete — case_id={case_id} "
            f"verdict={consensus.verdict} confidence={consensus.confidence}"
        )

    except Exception as exc:
        logger.exception(f"Pipeline failed — case_id={case_id}: {exc}")
        await _update_status(
            case_id,
            CaseStatus.FAILED,
            error_detail=str(exc),
        )
