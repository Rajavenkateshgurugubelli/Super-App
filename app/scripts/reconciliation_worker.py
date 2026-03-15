import os
import sys
import json
import logging
import datetime
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Wallet, Transaction
from apscheduler.schedulers.blocking import BlockingScheduler

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ReconciliationWorker")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../compliance_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def run_reconciliation():
    logger.info("Starting nightly ledger reconciliation...")
    session = SessionLocal()
    
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "wallets_scanned": 0,
        "discrepancies_found": 0,
        "details": []
    }
    
    try:
        wallets = session.query(Wallet).all()
        report["wallets_scanned"] = len(wallets)
        
        for wallet in wallets:
            # Sum of all credits (where this wallet is the receiver)
            credits = session.query(func.sum(Transaction.amount)).filter(
                Transaction.to_wallet_id == wallet.wallet_id,
                Transaction.status == "SUCCESS"
            ).scalar() or 0.0
            
            # Sum of all debits (where this wallet is the sender)
            debits = session.query(func.sum(Transaction.amount)).filter(
                Transaction.from_wallet_id == wallet.wallet_id,
                Transaction.status == "SUCCESS"
            ).scalar() or 0.0
            
            # Expected Balance
            expected_balance = credits - debits
            
            # Check for Discrepancy (Adding minor float tolerance)
            if abs(float(wallet.balance) - float(expected_balance)) > 0.01:
                logger.error(f"🚨 DISCREPANCY DETECTED: Wallet {wallet.wallet_id}. Expected: {expected_balance}, Actual: {wallet.balance}")
                report["discrepancies_found"] += 1
                report["details"].append({
                    "wallet_id": wallet.wallet_id,
                    "expected_balance": round(expected_balance, 2),
                    "actual_balance": round(float(wallet.balance), 2),
                    "variance": round(float(expected_balance) - float(wallet.balance), 2)
                })
        
        # Save Report
        date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        report_path = os.path.join(REPORTS_DIR, f"reconciliation_report_{date_str}.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=4)
            
        logger.info(f"Reconciliation complete. Report saved to {report_path}")
        if report["discrepancies_found"] > 0:
            logger.warning(f"⚠️ Found {report['discrepancies_found']} ledger discrepancies requiring manual audit.")
        else:
            logger.info("✅ All ledgers balanced successfully.")
            
    except Exception as e:
        logger.error(f"Failed during reconciliation: {e}")
    finally:
        session.close()

def start_scheduler():
    logger.info("Initializing APScheduler for Nightly Reconciliation...")
    scheduler = BlockingScheduler()
    
    # Run once immediately on startup
    run_reconciliation()
    
    # Schedule to run every day at midnight
    scheduler.add_job(run_reconciliation, 'cron', hour=0, minute=0)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()
