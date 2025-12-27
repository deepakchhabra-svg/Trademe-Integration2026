from retail_os.core.database import SessionLocal, SystemCommand

s = SessionLocal()
cmd = s.query(SystemCommand).filter_by(id='c654033c-7762-4282-afda-655da2e660ce').first()

print(f"Status: {cmd.status}")
print(f"Error Code: {cmd.error_code}")
print(f"Error Msg: {cmd.error_message}")
if cmd.payload and "balance_snapshot" in cmd.payload:
    print(f"Balance Snapshot: {cmd.payload['balance_snapshot']}")
else:
    print("Balance Snapshot: NOT FOUND")

s.close()
