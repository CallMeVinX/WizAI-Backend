"""Database seeding and bulk initialization utility.

Usage:
    python seed.py [--csv PATH] [--extract-sources] [--run-dedup] [--all]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
from app.models.lead import Lead
from app.models.dedupe import DedupeCandidate
from app.models.form_submission import FormSubmission
from app.services.csv_importer import import_csv
from app.services.source_extractor import extract_source
from app.services.dedupe_service import run_dedupe_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def seed_csv(csv_path: str, reset: bool = False):
    """Import CSV into database."""
    if reset:
        logger.info("Dropping existing tables for clean re-seed...")
        Base.metadata.drop_all(bind=engine)

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        try:
            existing = db.query(Lead).count()
        except Exception as e:
            logger.warning(f"Existing table schema mismatch ({e}). Recreating tables cleanly...")
            db.rollback()
            db.close()
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            existing = 0

        if existing > 0 and not reset:
            logger.warning(f"Database already has {existing} leads. Skipping CSV import.")
            logger.info("To reimport, run with --reset flag: python seed.py --all --reset")
            return existing

        logger.info(f"Importing CSV from: {csv_path}")
        count = import_csv(db, csv_path)
        logger.info(f"Successfully imported {count} leads")
        return count
    finally:
        db.close()


def run_source_extraction():
    """Run source extraction on all leads without ai_source_channel."""
    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(Lead.ai_source_channel.is_(None)).all()
        logger.info(f"Running source extraction on {len(leads)} leads...")

        rule_count = 0
        llm_count = 0
        fail_count = 0

        for i, lead in enumerate(leads):
            if not lead.notes:
                lead.ai_source_channel = "Other"
                lead.ai_source_detail = "No notes available"
                fail_count += 1
                continue

            try:
                # Try rules first (extract_source handles this internally)
                from app.services.source_extractor import extract_source_rules
                result = extract_source_rules(lead.notes)
                if result:
                    lead.ai_source_channel, lead.ai_source_detail = result
                    rule_count += 1
                else:
                    # Fallback to 'Other' when rule extraction does not match to prevent external API rate-limiting during bulk seed
                    lead.ai_source_channel = "Other"
                    lead.ai_source_detail = "Rule-based extraction did not match"
                    fail_count += 1
            except Exception as e:
                logger.error(f"Source extraction failed for lead {lead.id}: {e}")
                fail_count += 1

            if (i + 1) % 100 == 0:
                db.commit()
                logger.info(f"Processed {i + 1}/{len(leads)} leads...")

        db.commit()
        logger.info(
            f"Source extraction complete: {rule_count} rule-matched, "
            f"{llm_count} LLM-matched, {fail_count} unmatched"
        )
    finally:
        db.close()


def run_dedup():
    """Run dedup pipeline."""
    db = SessionLocal()
    try:
        logger.info("Running dedup pipeline...")
        results = run_dedupe_pipeline(db)
        logger.info(f"Dedup complete: {len(results)} candidate pairs found")
    finally:
        db.close()


def get_default_csv_path() -> str:
    candidates = [
        Path(__file__).parent / "data" / "leads_seed.csv",
        Path(__file__).parent.parent / "data" / "leads_seed.csv",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return str(candidates[0])


def main():
    parser = argparse.ArgumentParser(description="Seed the WizzAI Lead Management database")
    parser.add_argument(
        "--csv",
        default=get_default_csv_path(),
        help="Path to leads_seed.csv",
    )
    parser.add_argument("--extract-sources", action="store_true", help="Run AI source extraction")
    parser.add_argument("--run-dedup", action="store_true", help="Run dedup pipeline")
    parser.add_argument("--all", action="store_true", help="Run all steps (import + extract + dedup)")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate tables before seeding")

    args = parser.parse_args()

    # Step 1: Import CSV
    seed_csv(args.csv, reset=args.reset)

    # Step 2: Source extraction
    if args.extract_sources or args.all:
        run_source_extraction()

    # Step 3: Dedup
    if args.run_dedup or args.all:
        run_dedup()

    logger.info("Seed complete!")


if __name__ == "__main__":
    main()
