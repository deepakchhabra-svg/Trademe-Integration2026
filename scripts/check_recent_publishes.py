from retail_os.core.database import SessionLocal, SystemCommand, TradeMeListing
import json

s = SessionLocal()
cmds = s.query(SystemCommand).filter(SystemCommand.type == 'PUBLISH_LISTING', SystemCommand.status == 'SUCCEEDED').order_by(SystemCommand.updated_at.desc()).limit(3).all()

for c in cmds:
    print(f"--- Command ID: {c.id} ---")
    prod_id = c.payload.get('internal_product_id')
    tm = s.query(TradeMeListing).filter_by(internal_product_id=prod_id).first()
    if tm:
        print(f"Actual State: {tm.actual_state}")
        try:
            payload = json.loads(tm.payload_snapshot)
            desc = payload.get("Description", [""])[0]
            print(f"Description Snippet:\n{desc[:500]}")
        except:
             print(f"Raw Payload: {tm.payload_snapshot[:200]}")
    print("\n")

s.close()
