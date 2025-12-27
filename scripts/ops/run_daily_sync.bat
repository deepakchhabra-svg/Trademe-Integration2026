@echo off
cd /d "c:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration"
echo Starting Unified Sync Pipeline...
python scripts\run_unified_pipeline.py --batch-size 50
echo Sync Complete.
pause
