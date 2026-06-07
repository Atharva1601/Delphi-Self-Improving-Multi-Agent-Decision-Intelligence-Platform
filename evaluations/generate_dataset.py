"""
evaluations/generate_dataset.py
───────────────────────────────
Generates 50–100 diverse decision queries across five target domains:
  - Healthcare
  - Finance
  - Enterprise Technology
  - Cybersecurity
  - Startups

Uses Groq API to generate queries dynamically if keys are configured;
otherwise, falls back to a high-quality, pre-defined static dataset.
"""
import os
import sys
import json
import asyncio
from pathlib import Path

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.config import settings

# Fallback scenarios to ensure offline/mock robustness
FALLBACK_SCENARIOS = [
    # ── Healthcare (15 Scenarios) ──
    {"id": "hc-01", "domain": "Healthcare", "query": "Should we deploy a clinical AI diagnostic tool in our ER department for real-time triage?", "complexity": "high"},
    {"id": "hc-02", "domain": "Healthcare", "query": "Should a regional hospital network transition 100% of non-emergency patient consultations to a telehealth-first model?", "complexity": "medium"},
    {"id": "hc-03", "domain": "Healthcare", "query": "Should we integrate semi-autonomous surgical robotic arms in our orthopedic surgery department?", "complexity": "high"},
    {"id": "hc-04", "domain": "Healthcare", "query": "Should we implement a cloud-based EHR (Electronic Health Record) system sharing patient records across regional clinics?", "complexity": "medium"},
    {"id": "hc-05", "domain": "Healthcare", "query": "Should our research hospital utilize LLM-based agents to parse medical history and recommend clinical trial candidates?", "complexity": "high"},
    {"id": "hc-06", "domain": "Healthcare", "query": "Should we deploy AI-driven prescription monitoring systems to flag potential drug abuse patterns in real-time?", "complexity": "high"},
    {"id": "hc-07", "domain": "Healthcare", "query": "Should we replace manual nurse scheduling with a dynamic, AI-optimized predictive staffing algorithm?", "complexity": "low"},
    {"id": "hc-08", "domain": "Healthcare", "query": "Should we integrate remote patient monitoring wearables for post-op heart surgery patients?", "complexity": "medium"},
    {"id": "hc-09", "domain": "Healthcare", "query": "Should we implement automated voice-to-text scribes for all clinical patient notes during doctor visits?", "complexity": "low"},
    {"id": "hc-10", "domain": "Healthcare", "query": "Should a pediatric clinic group mandate genetic screening compatibility profiles for standard oncology treatments?", "complexity": "high"},
    {"id": "hc-11", "domain": "Healthcare", "query": "Should we deploy autonomous disinfection robots across all patient wards and hallways?", "complexity": "low"},
    {"id": "hc-12", "domain": "Healthcare", "query": "Should we outsource clinical billing and claims processing entirely to a third-party automated fintech vendor?", "complexity": "medium"},
    {"id": "hc-13", "domain": "Healthcare", "query": "Should we deploy computer-vision models to audit surgical instrument counts before closing patients?", "complexity": "medium"},
    {"id": "hc-14", "domain": "Healthcare", "query": "Should we use patient-facing conversational chatbots to diagnose mild symptoms and recommend over-the-counter medicine?", "complexity": "high"},
    {"id": "hc-15", "domain": "Healthcare", "query": "Should our radiology clinic use deep-learning classifiers as a primary, automated screen for lung nodules, bypassing human reads for low-risk cases?", "complexity": "high"},

    # ── Finance (15 Scenarios) ──
    {"id": "fin-01", "domain": "Finance", "query": "Should a digital banking startup launch a fully autonomous, AI-driven lending platform offering loans up to $50,000?", "complexity": "high"},
    {"id": "fin-02", "domain": "Finance", "query": "Should a mid-sized asset manager transition 50% of active equity portfolios to quantitative, AI-rebalanced index funds?", "complexity": "high"},
    {"id": "fin-03", "domain": "Finance", "query": "Should our credit card company deploy real-time transaction blocking powered by graph-neural-network fraud models?", "complexity": "high"},
    {"id": "fin-04", "domain": "Finance", "query": "Should we integrate cryptocurrency transactions and stablecoin holdings into our consumer banking application?", "complexity": "high"},
    {"id": "fin-05", "domain": "Finance", "query": "Should we automate our mortgage underwriting process, making loan decisions in under 60 seconds using alternative data?", "complexity": "high"},
    {"id": "fin-06", "domain": "Finance", "query": "Should our commercial bank launch an automated trade finance portal powered by smart contracts on a permissioned ledger?", "complexity": "medium"},
    {"id": "fin-07", "domain": "Finance", "query": "Should we replace our customer service call center with LLM-powered financial advisory agents?", "complexity": "high"},
    {"id": "fin-08", "domain": "Finance", "query": "Should a community bank launch a digital micro-savings product aimed at high-school students?", "complexity": "low"},
    {"id": "fin-09", "domain": "Finance", "query": "Should we deploy natural language processing systems to perform real-time sentiment analysis on social media for high-frequency trading inputs?", "complexity": "high"},
    {"id": "fin-10", "domain": "Finance", "query": "Should we mandate biometric facial scans for all wire transfers exceeding $10,000 to combat fraud?", "complexity": "medium"},
    {"id": "fin-11", "domain": "Finance", "query": "Should our retail bank outsource its core ledger database to a multi-cloud managed service?", "complexity": "medium"},
    {"id": "fin-12", "domain": "Finance", "query": "Should we offer customized, dynamic interest rates based on real-time open banking transactional analysis?", "complexity": "medium"},
    {"id": "fin-13", "domain": "Finance", "query": "Should we build an internal predictive tool for macroeconomic forecasting to drive our commercial real estate lending portfolio?", "complexity": "medium"},
    {"id": "fin-14", "domain": "Finance", "query": "Should we invest in tokenizing physical real estate assets to offer fractional ownership to retail investors?", "complexity": "medium"},
    {"id": "fin-15", "domain": "Finance", "query": "Should our investment bank mandate that all research analysts use AI tools to auto-generate draft equity research reports?", "complexity": "low"},

    # ── Enterprise Technology (15 Scenarios) ──
    {"id": "et-01", "domain": "Enterprise Technology", "query": "Should our legacy enterprise migrate its core relational database to a distributed, multi-region SQL database?", "complexity": "medium"},
    {"id": "et-02", "domain": "Enterprise Technology", "query": "Should we enforce a mandatory shift from a monolithic application architecture to microservices running on Kubernetes?", "complexity": "high"},
    {"id": "et-03", "domain": "Enterprise Technology", "query": "Should we replace our internal VPN with a software-defined perimeter and Zero Trust Network Access architecture?", "complexity": "high"},
    {"id": "et-04", "domain": "Enterprise Technology", "query": "Should we mandate the use of AI coding assistants for all software engineering teams to improve velocity?", "complexity": "low"},
    {"id": "et-05", "domain": "Enterprise Technology", "query": "Should we build a centralized enterprise data mesh to enable individual business units to query clean data directly?", "complexity": "medium"},
    {"id": "et-06", "domain": "Enterprise Technology", "query": "Should we migrate our entire server infrastructure from AWS to a hybrid on-premises and private cloud setup?", "complexity": "high"},
    {"id": "et-07", "domain": "Enterprise Technology", "query": "Should we build an in-house LLM search engine to index all internal chats, documentation, and emails?", "complexity": "medium"},
    {"id": "et-08", "domain": "Enterprise Technology", "query": "Should we implement automated CI/CD security scanning that auto-blocks commits with dependency vulnerabilities?", "complexity": "medium"},
    {"id": "et-09", "domain": "Enterprise Technology", "query": "Should we replace Slack and Teams with a custom, self-hosted, secure open-source communication platform?", "complexity": "low"},
    {"id": "et-10", "domain": "Enterprise Technology", "query": "Should we mandate that all customer-facing applications support offline-first sync architecture?", "complexity": "medium"},
    {"id": "et-11", "domain": "Enterprise Technology", "query": "Should we implement real-time employee productivity monitoring tools based on desktop activity metrics?", "complexity": "high"},
    {"id": "et-12", "domain": "Enterprise Technology", "query": "Should we shift our API architecture from REST to GraphQL for all internal and external services?", "complexity": "low"},
    {"id": "et-13", "domain": "Enterprise Technology", "query": "Should we implement a policy that forbids the use of any open-source code libraries not audited by our security committee?", "complexity": "medium"},
    {"id": "et-14", "domain": "Enterprise Technology", "query": "Should we build a unified mobile app that merges all internal HR, IT support, and expense filing into one client?", "complexity": "low"},
    {"id": "et-15", "domain": "Enterprise Technology", "query": "Should we deploy serverless computing (AWS Lambda / Cloudflare Workers) as the default architecture for all new service builds?", "complexity": "medium"},

    # ── Cybersecurity (15 Scenarios) ──
    {"id": "sec-01", "domain": "Cybersecurity", "query": "Should we deploy a centralized automated threat hunting agent with write-access to firewall configuration rules?", "complexity": "high"},
    {"id": "sec-02", "domain": "Cybersecurity", "query": "Should our enterprise mandate passwordless biometric-only authentication for all corporate devices and accounts?", "complexity": "medium"},
    {"id": "sec-03", "domain": "Cybersecurity", "query": "Should we shift from annual external penetration testing to a continuous, automated breach and attack simulation (BAS) system?", "complexity": "medium"},
    {"id": "sec-04", "domain": "Cybersecurity", "query": "Should we implement full-disk hardware encryption across all corporate laptops, with keys escrowed in a cloud HSM?", "complexity": "low"},
    {"id": "sec-05", "domain": "Cybersecurity", "query": "Should we route all corporate network traffic through a cloud-based Secure Access Service Edge (SASE) system?", "complexity": "medium"},
    {"id": "sec-06", "domain": "Cybersecurity", "query": "Should we establish a formal bug bounty program with public payouts ranging from $500 to $50,000?", "complexity": "medium"},
    {"id": "sec-07", "domain": "Cybersecurity", "query": "Should we block access to all personal email, file sharing, and social media sites from corporate networks and devices?", "complexity": "medium"},
    {"id": "sec-08", "domain": "Cybersecurity", "query": "Should we integrate automated canary databases inside our network to detect and isolate ransomware encryption activity early?", "complexity": "high"},
    {"id": "sec-09", "domain": "Cybersecurity", "query": "Should we deploy machine-learning endpoint detection agents that can quarantine devices without human analyst sign-off?", "complexity": "high"},
    {"id": "sec-10", "domain": "Cybersecurity", "query": "Should we implement a policy requiring all employees to undergo monthly, unannounced simulated phishing tests?", "complexity": "low"},
    {"id": "sec-11", "domain": "Cybersecurity", "query": "Should we migrate our Security Operations Center (SOC) from an outsourced managed service to an in-house 24/7 team?", "complexity": "high"},
    {"id": "sec-12", "domain": "Cybersecurity", "query": "Should we enforce container image signing and strict runtime isolation for all production workloads?", "complexity": "medium"},
    {"id": "sec-13", "domain": "Cybersecurity", "query": "Should we transition all database encryption from transparent data encryption (TDE) to fully homomorphic encryption (FHE)?", "complexity": "high"},
    {"id": "sec-14", "domain": "Cybersecurity", "query": "Should we blacklist all developer access to generative AI websites to prevent intellectual property leaks?", "complexity": "medium"},
    {"id": "sec-15", "domain": "Cybersecurity", "query": "Should we deploy internal network honeypots masquerading as high-value database servers to capture insider threats?", "complexity": "medium"},

    # ── Startups (15 Scenarios) ──
    {"id": "st-01", "domain": "Startups", "query": "Should our seed-stage startup hire sales reps in Europe using an Employer of Record (EoR) before establishing legal entities?", "complexity": "low"},
    {"id": "st-02", "domain": "Startups", "query": "Should we pivot our B2C fintech mobile app to an enterprise B2B SaaS white-labeled API model?", "complexity": "high"},
    {"id": "st-03", "domain": "Startups", "query": "Should we build our product MVP using no-code/low-code tools to launch in 4 weeks instead of coding it from scratch?", "complexity": "low"},
    {"id": "st-04", "domain": "Startups", "query": "Should we raise a down-round valuation bridge to extend our runway by 9 months rather than cutting staff by 40%?", "complexity": "high"},
    {"id": "st-05", "domain": "Startups", "query": "Should we open-source our core software engine to drive developer adoption and shift to a paid enterprise cloud model?", "complexity": "high"},
    {"id": "st-06", "domain": "Startups", "query": "Should our startup transition to a 100% remote-work model, closing our physical headquarters permanently?", "complexity": "low"},
    {"id": "st-07", "domain": "Startups", "query": "Should we allocate 30% of our seed marketing budget to influencer campaigns on TikTok and YouTube rather than standard search ads?", "complexity": "medium"},
    {"id": "st-08", "domain": "Startups", "query": "Should we offer customer lifetime value (LTV) discount packages (e.g., $999 for lifetime access) to boost immediate cash flow?", "complexity": "medium"},
    {"id": "st-09", "domain": "Startups", "query": "Should we license our core patent to our main competitor in exchange for a 10% royalty stream and market-sharing agreements?", "complexity": "high"},
    {"id": "st-10", "domain": "Startups", "query": "Should we prioritize hiring a senior product manager over a lead infrastructure engineer for our next 2 hires?", "complexity": "medium"},
    {"id": "st-11", "domain": "Startups", "query": "Should we offer all early employees equity compensation in lieu of market-rate cash salaries to conserve our remaining capital?", "complexity": "medium"},
    {"id": "st-12", "domain": "Startups", "query": "Should we expand our localization to 5 new languages simultaneously to capture international market share early?", "complexity": "medium"},
    {"id": "st-13", "domain": "Startups", "query": "Should we build a proprietary LLM foundation model instead of fine-tuning existing open-source models (like Llama/Mistral)?", "complexity": "high"},
    {"id": "st-14", "domain": "Startups", "query": "Should we outsource customer support to an offshore vendor to lower monthly operating expenses?", "complexity": "low"},
    {"id": "st-15", "domain": "Startups", "query": "Should our startup acquire a smaller failing competitor for their engineering talent via an stock-only transaction?", "complexity": "high"}
]


async def generate_via_llm(domain: str, count: int = 15) -> list[dict]:
    """Generates scenario queries dynamically using the Groq API."""
    from groq import AsyncGroq
    from pydantic import BaseModel, Field

    class Scenario(BaseModel):
        query: str = Field(..., description="A realistic, detailed, and highly strategic decision query.")
        complexity: str = Field(..., description="Complexity of the scenario: 'low', 'medium', or 'high'")

    class GenerationResponse(BaseModel):
        scenarios: list[Scenario]

    client = AsyncGroq(api_key=settings.groq_api_key)
    system_prompt = (
        f"You are a strategic decision expert. Your task is to generate {count} highly realistic, "
        f"challenging, and detailed business decision queries for the domain '{domain}'. "
        "Each query must be structured as a question starting with 'Should we...', 'Should a...', or 'Should our...', "
        "and present a trade-off (e.g., capital cost vs. efficiency, security vs. convenience, speed vs. reliability). "
        "Ensure the queries sound professional and fit for evaluation by an expert council."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.agent_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate {count} scenarios for the {domain} domain in JSON format."}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
            max_tokens=2048,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        
        # Simple parsing & domain mapping
        raw_scenarios = data.get("scenarios", [])
        scenarios = []
        for i, raw in enumerate(raw_scenarios):
            scenarios.append({
                "id": f"{domain[:2].lower()}-{i+1:02d}",
                "domain": domain,
                "query": raw.get("query"),
                "complexity": raw.get("complexity", "medium")
            })
        return scenarios
    except Exception as exc:
        print(f"  [!] Failed to generate via LLM for {domain}: {exc}. Using fallbacks.")
        # Return fallback items matching this domain
        return [s for s in FALLBACK_SCENARIOS if s["domain"] == domain][:count]


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Delphi Evaluation Dataset Generator")
    parser.add_argument("--live", action="store_true", help="Generate scenarios using the live LLM API.")
    args = parser.parse_args()

    print("=== Delphi Evaluation Dataset Generator ===")
    
    # Check if Groq is available & valid
    is_live = False
    if args.live and settings.groq_api_key and not settings.groq_api_key.startswith("gsk_dummy") and "gsk_" in settings.groq_api_key:
        is_live = True
        print("[*] Groq API Key found. Generating dataset using LLM...")
    elif args.live:
        print("[!] Live mode requested, but Groq API Key is missing or invalid. Falling back to static scenarios...")
    else:
        print("[*] Seeding dataset with pre-defined scenarios...")

    domains = ["Healthcare", "Finance", "Enterprise Technology", "Cybersecurity", "Startups"]
    dataset = []

    if is_live:
        for domain in domains:
            print(f"Generating scenarios for {domain}...")
            domain_scenarios = await generate_via_llm(domain, count=15)
            print(f"  Generated {len(domain_scenarios)} scenarios.")
            dataset.extend(domain_scenarios)
            await asyncio.sleep(1.0) # Rate limit cooling
    else:
        dataset = FALLBACK_SCENARIOS
        print(f"Successfully loaded {len(dataset)} pre-defined scenarios.")

    # Write dataset to evaluations/dataset.json
    output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "dataset.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"[*] Dataset successfully saved to: {output_path.resolve()}")
    print("=== Done ===")

if __name__ == "__main__":
    asyncio.run(main())
