
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime,timezone, timedelta
import os
import subprocess

LOCAL_TZ = timezone(timedelta(hours=8))
RETRY_ENABLED = os.getenv("RETRY", "false").lower() == "true"
Pybin="/venv/bin/python"
task="zampto_server.py"
def log(message: str, retry=False):
    now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    if retry:
        task_type="retry"
    else:
        task_type="standard"
    print(f"[{now}] [{task_type}] {message}")

def job(retry=False):
    result = subprocess.run([Pybin, task])
    if result.returncode == 0:
        log("✅ corn task excuted success",retry)
    else:
        log(f"❌ corn task excuted executed fail，exit code is {result.returncode}",retry)
        if RETRY_ENABLED and not retry:
            scheduler.add_job(job, 'date', 
            run_date=datetime.now() + timedelta(hours=1)
            ,kwargs={'retry': True})

scheduler = BlockingScheduler(timezone=LOCAL_TZ)

scheduler.add_job(job, 'interval', seconds=10, next_run_time=datetime.now(LOCAL_TZ))

scheduler.start()
