# Operator Standard Operating Procedure (SOP)

## Trade Me Ops System — Daily Operations Guide

**Version**: 1.0  
**Last Updated**: 2026-01-02  
**Audience**: Store operators with minimal technical background

---

## Quick Reference Card

| Task | Where | Button |
|------|-------|--------|
| Check store health | Dashboard | (View only) |
| Get new products | Pipeline → Supplier → "Refresh Products" | 🔄 |
| Enrich with AI | Pipeline → Supplier → "AI Enrich" | ✨ |
| Review before publish | Publish Console → "Preview" | 👁️ |
| Publish to Trade Me | Publish Console → "Publish" | ✅ |
| Check failures | Jobs → Attention Required | 🔴 |
| Retry a failed job | Jobs → [Job] → "Retry" | 🔄 |
| Process an order | Fulfillment → Pending | 📦 |

---

## Daily Routine (15-20 minutes)

### 1. Morning Health Check (5 min)
**Go to**: Dashboard (home page)

✅ **Check these items:**
- [ ] "Failed Jobs" card = 0 (if not, go to Jobs first)
- [ ] "Pending Orders" = handle before anything else
- [ ] API Status = GREEN
- [ ] Last Scrape = within 24 hours

⚠️ **If API Status is RED**: Wait 15 minutes and refresh. If still red, contact support.

---

### 2. Process Inbox Failures (if any)
**Go to**: Jobs → Attention Required

For each failed job:
1. **Open** the job to read the error
2. **Common fixes:**
   - "Rate limit exceeded" → Wait 1 hour, then **Retry**
   - "Image download failed" → **Retry** (usually works on second try)
   - "Category not found" → **Dismiss** and note the product SKU
   - "Trade Me API error" → **Retry** once, if still fails, **Dismiss**

3. After fixing all failures, dashboard should show "Failed Jobs: 0"

---

### 3. Refresh Product Inventory (5 min)
**Go to**: Pipeline → Select Supplier (e.g., OneCheq)

**Run in order:**
1. Click **"Refresh Products"** (🔄)
   - Wait for "Job started" message
   - This imports new/updated products from supplier

2. Click **"AI Enrich"** (✨)
   - Wait for "Job started" message
   - This creates professional titles/descriptions

3. Click **"Prepare for Publish"** (📝)
   - This creates draft listings for review

4. Note the number shown: "X products ready for review"

---

### 4. Review and Publish (5 min)
**Go to**: Publish Console

1. Click **"Preview"** to see what will be published
2. Review the list:
   - ✅ Green items are ready
   - ⚠️ Yellow items have warnings (missing images, etc.)
   - ❌ Red items will not publish (fix required)

3. If everything looks good:
   - Click **"Publish to Trade Me"**
   - Confirm in the popup
   - You'll see "X listings published" confirmation

---

### 5. Process Orders
**Go to**: Fulfillment

For each pending order:
1. Open order details
2. Verify item is in stock at supplier
3. Place order with supplier
4. Mark as "Dispatched" with tracking number
5. Buyer is automatically notified

---

## When Something Fails

### Error: "Job stuck in RUNNING for hours"
**Action**: Go to Jobs → find the job → click "Cancel" → then "Retry"

### Error: "Trade Me API Error 403"
**Action**: Check Trade Me Account page (Advanced → Trade Me Account)
- If balance is negative: Top up account first
- If tokens expired: Contact support for re-authentication

### Error: "No products found after scrape"
**Possible causes**:
1. Supplier website is down → Wait and retry later
2. Supplier changed their page layout → Contact support
3. Network issue → Retry in 30 minutes

### Error: "Duplicate listing detected"
**Action**: Go to Advanced → Duplicate Manager → Auto-Resolve

---

## Weekly Tasks

### Monday: Reprice Review
**Go to**: Publish Console → Reprice Tab

1. Click **"Calculate New Prices"** (preview only)
2. Review proposed price changes
3. If OK, click **"Apply Price Changes"**

### Friday: Cleanup
**Go to**: Advanced → Unavailable Items

1. Review items no longer at supplier
2. Click **"Withdraw from Trade Me"** for confirmed unavailable items

---

## Escalation Contacts

| Issue | Contact | Response Time |
|-------|---------|---------------|
| System down | [Support Email] | 4 hours |
| Trade Me API issues | [Support Email] | Same day |
| Feature request | [Support Email] | Best effort |

---

## Glossary

| Term | Meaning |
|------|---------|
| Pipeline | Where products flow: Supplier → AI Enrich → Draft → Live |
| Job | A background task (scrape, enrich, publish, etc.) |
| Draft | A listing preview before publishing to Trade Me |
| Live | Actually on Trade Me and for sale |
| Dismiss | Mark a failed job as "handled" (won't retry) |
| Reconcile | Compare our records with Trade Me's actual state |

---

## Do NOT Do

❌ **Never** click "Apply Price Changes" without reviewing the preview first  
❌ **Never** dismiss a failed job without reading the error  
❌ **Never** run "Withdraw" without checking the list first  
❌ **Never** skip the morning health check  

---

*This SOP matches UI as of version 1.0. If buttons look different, contact support for updated documentation.*
