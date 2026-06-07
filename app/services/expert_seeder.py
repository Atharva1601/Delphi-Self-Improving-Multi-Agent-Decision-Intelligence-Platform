"""
app/services/expert_seeder.py
──────────────────────────────
Seeds the 7 permanent Delphi experts into the database on startup.
This is idempotent — if an expert already exists (by name), it is skipped.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.expert import Expert
from loguru import logger

PERMANENT_EXPERTS = [
    {
        "name": "Finance Expert",
        "domain": "finance",
        "description": (
            "Analyses financial risks, ROI, capital allocation, market valuation, "
            "budget impact, and economic implications of strategic decisions."
        ),
    },
    {
        "name": "Legal Expert",
        "domain": "legal",
        "description": (
            "Evaluates regulatory compliance, contractual risks, liability exposure, "
            "intellectual property, and legal constraints across jurisdictions."
        ),
    },
    {
        "name": "Security Expert",
        "domain": "security",
        "description": (
            "Assesses cybersecurity threats, data privacy risks, infrastructure "
            "vulnerabilities, and compliance with security standards (SOC2, ISO27001)."
        ),
    },
    {
        "name": "Technical Architect Expert",
        "domain": "technical",
        "description": (
            "Reviews system architecture, scalability, technical debt, integration "
            "complexity, engineering feasibility, and platform risks."
        ),
    },
    {
        "name": "Operations Expert",
        "domain": "operations",
        "description": (
            "Examines operational feasibility, process efficiency, supply chain, "
            "resource capacity, change management, and execution risks."
        ),
    },
    {
        "name": "Product Strategy Expert",
        "domain": "product_strategy",
        "description": (
            "Evaluates product-market fit, user experience impact, roadmap alignment, "
            "competitive differentiation, and feature prioritisation trade-offs."
        ),
    },
    {
        "name": "Business Market Expert",
        "domain": "business",
        "description": (
            "Analyses market opportunity, competitive landscape, go-to-market strategy, "
            "customer segments, revenue models, and business case strength."
        ),
    },
]


async def seed_experts() -> None:
    """
    Insert permanent experts if they do not already exist.
    Called during application startup via lifespan.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for expert_data in PERMANENT_EXPERTS:
                result = await session.execute(
                    select(Expert).where(Expert.name == expert_data["name"])
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    session.add(Expert(**expert_data))
                    logger.info(f"Seeded expert: {expert_data['name']}")
                else:
                    logger.debug(f"Expert already exists: {expert_data['name']}")

    logger.info("Expert seeding complete.")
