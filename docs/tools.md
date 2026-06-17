# Tool reference

All tools accept an optional `party_id` argument that overrides the configured
PartyID for that single call — handy for accountant-style "switch company"
workflows.

## Orders

| Tool | Purpose | Read-only |
|---|---|---|
| `list_orders` | List invoices, credit notes, offers; filter by type, direction, search | ✅ |
| `get_order` | Fetch one order with lines, attachments, PDF file ID | ✅ |
| `list_deleted_orders` | Show soft-deleted orders | ✅ |
| `create_invoice` | Create a sales invoice (returns OrderID) | |
| `create_credit_note` | Create a credit note — `about_invoice_number` links to original | |
| `create_offer` | Create a sales offer / quote | |
| `update_order` | PATCH any order field (cancel via `OrderStatus='Canceled'`) | |
| `delete_order` | Soft-delete an order | destructive |
| `send_orders` | Send via SMTP, Peppol, Letter, SDI, KSeF, … | |
| `record_payment` | Record a full or partial payment | |

## Parties

| Tool | Purpose | Read-only |
|---|---|---|
| `list_parties` | List customers and/or suppliers | ✅ |
| `get_party` | Fetch one party by resource ID | ✅ |
| `find_party_by_vat` | Look up a party by VAT number | ✅ |
| `create_party` | Create a customer or supplier | idempotent on VAT |
| `update_party` | PATCH party fields | |

## Products

| Tool | Purpose | Read-only |
|---|---|---|
| `list_products` | List catalogue products | ✅ |
| `get_product` | Fetch one product | ✅ |
| `upsert_product` | Upsert by reference (SKU) | idempotent |

## Documents

| Tool | Purpose | Read-only |
|---|---|---|
| `list_documents` | List documents stored against the PartyID | ✅ |
| `get_document` | Fetch one document's metadata | ✅ |
| `upload_document` | Upload a file (base64 inline) | |

## Files

| Tool | Purpose | Read-only |
|---|---|---|
| `download_file` | Download by UUID. Returns base64 or saves to disk if `save_to` provided | ✅ |

## Reports

| Tool | Purpose | Read-only |
|---|---|---|
| `list_reports` | Available reports | ✅ |
| `get_report` | Fetch CSV results | ✅ |

## Peppol

| Tool | Purpose | Auth |
|---|---|---|
| `lookup_peppol_participant` | Look up any company on Peppol by VAT/CBE — **no auth required** | — |
| `list_peppol_inbox` | Inbound Peppol documents (first 10) | apikey/oauth |
| `confirm_peppol_inbox` | Accept an inbound document | apikey/oauth |
| `refuse_peppol_inbox` | Reject an inbound document | apikey/oauth |
| `register_peppol_participant` | Register the current company on Peppol | apikey/oauth |

## Inbox / OCR

| Tool | Purpose | Read-only |
|---|---|---|
| `submit_inbound_pdf` | Upload a supplier PDF; Billit OCRs it into a Cost order | |
| `list_inbound_queue` | Show items currently being processed | ✅ |

## Account

| Tool | Purpose | Read-only |
|---|---|---|
| `get_account_info` | Current company, license, addons, sequences. **Connectivity smoke test.** | ✅ |

## ChatGPT-compat

| Tool | Purpose | Read-only |
|---|---|---|
| `search` | Cross-resource search returning `{results: [{id, title, url}]}` | ✅ |
| `fetch` | Fetch by ID returned from `search`; returns text + metadata | ✅ |

## Common arguments

- `party_id` — override the configured PartyID. Pass an integer-as-string.
- `idempotent_key` — for any POST tool. Auto-filled with a UUID if omitted;
  pass your own for client-side dedupe across retries.
