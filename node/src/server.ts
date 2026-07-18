/** Builds the MCP server with all Billit tools registered. Transport-agnostic. */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { BillitClient } from "./client.js";
import type { BillitConfig } from "./config.js";
import { isProduction } from "./config.js";
import * as documents from "./tools/documents.js";
import * as misc from "./tools/misc.js";
import * as orders from "./tools/orders.js";
import * as parties from "./tools/parties.js";
import * as peppol from "./tools/peppol.js";
import * as products from "./tools/products.js";
import * as searchFetch from "./tools/searchFetch.js";

export const VERSION = "0.1.0";

const INSTRUCTIONS = `\
Billit MCP — manage Belgian e-invoices (Orders), customers/suppliers (Parties),
products, documents, Peppol participants, and inbound OCR.

Key concepts:
- Every API call is scoped to a Billit company via PartyID; the server's
  PartyID is configured at startup but can be overridden per call.
- Orders is one resource for invoices, credit notes and offers — discriminate
  by order_type ("Invoice" | "CreditNote" | "Offer") and order_direction
  ("Income" for sales / "Cost" for purchase).
- Credit notes link to the original invoice via about_invoice_number.
- Sending (email/Peppol/letter) is a separate step from creating: use
  send_orders with the right transport_type after create_invoice.
- Idempotency: create/send tools accept idempotent_key; a UUID is generated
  per call if omitted.

Safety: the default base URL is sandbox. Destructive tools (delete_order,
send_orders) should prompt for confirmation in your client.`;

export function buildServer(cfg: BillitConfig): { server: McpServer; client: BillitClient } {
  const client = new BillitClient(cfg);
  const envLabel = isProduction(cfg) ? "PRODUCTION" : "sandbox";
  const server = new McpServer(
    { name: "billit", version: VERSION },
    { instructions: `${INSTRUCTIONS}\n\nActive environment: ${envLabel} (${cfg.baseUrl}).` },
  );

  orders.register(server, client);
  parties.register(server, client);
  products.register(server, client);
  documents.register(server, client);
  peppol.register(server, client);
  misc.register(server, client);
  searchFetch.register(server, client);

  return { server, client };
}
