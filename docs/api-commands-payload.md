# API Commands Payload Reference

## 1. General Enqueue (`POST /ops/enqueue`)
**Description:** Manually enqueue any system command. Used for one-off tasks.

**Payload (`EnqueueRequest`):**
```json
{
  "type": "SCRAPE_SUPPLIER",  // Required (Command Type)
  "payload": {                // Optional (Command Arguments)
    "supplier_id": 1,
    "pages": 5
  },
  "priority": 50              // Optional (Default: 50)
}
```

## 2. Bulk Dry Run (`POST /ops/bulk/dryrun_publish`)
**Description:** Generates `PUBLISH_LISTING` commands in `dry_run=True` mode for human review.

**Payload (`BulkDryRunPublishRequest`):**
```json
{
  "supplier_id": 1,           // Optional filter
  "source_category": "Laptops", // Optional filter
  "limit": 50,                // Default: 50
  "priority": 60,             // Default: 60
  "stop_on_failure": true     // Default: true (Safety gate)
}
```

## 3. Bulk Approve Publish (`POST /ops/bulk/approve_publish`)
**Description:** Converts reviewed `DRY_RUN` listings into real `PUBLISH_LISTING` commands (Live mode). Note: Performs tight hash validation.

**Payload (`BulkApprovePublishRequest`):**
```json
{
  "supplier_id": 1,
  "source_category": "Laptops",
  "limit": 50,
  "priority": 60,
  "stop_on_failure": true
}
```

## 4. Bulk Withdraw Removed (`POST /ops/bulk/withdraw_removed`)
**Description:** Enqueues `WITHDRAW_LISTING` for items marked as `REMOVED` by the synchronizer.

**Payload (`BulkWithdrawRemovedRequest`):**
```json
{
  "supplier_id": 1            // Optional
}
```
