/** Product catalogue tools. */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { dropNone, odataParams, run } from "./util.js";

const partyIdArg = z.string().optional().describe("Override the default PartyID for this call.");

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "list_products",
    {
      title: "List products",
      description: "List catalogue products.",
      inputSchema: {
        search: z.string().optional(),
        top: z.number().int().min(1).max(200).default(50),
        skip: z.number().int().min(0).default(0),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ search, top, skip, party_id }) =>
      run(() =>
        client.get("products", {
          params: odataParams({ top, skip, fullTextSearch: search }),
          partyId: party_id,
        }),
      ),
  );

  server.registerTool(
    "get_product",
    {
      title: "Get product",
      description: "Fetch one product by ID.",
      inputSchema: { product_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ product_id, party_id }) =>
      run(() => client.get(`products/${product_id}`, { partyId: party_id })),
  );

  server.registerTool(
    "upsert_product",
    {
      title: "Upsert product",
      description: "Create or update a product by reference (SKU).",
      inputSchema: {
        reference: z.string().describe("Your SKU / internal reference. Acts as upsert key."),
        description: z.string(),
        amount_excl: z.number(),
        vat_percentage: z.number().default(21),
        unit: z.string().optional(),
        ean: z.string().optional(),
        idempotent_key: z.string().optional(),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, idempotentHint: true, openWorldHint: true },
    },
    ({ reference, description, amount_excl, vat_percentage, unit, ean, idempotent_key, party_id }) =>
      run(async () => {
        const result = await client.post("products", {
          body: dropNone({
            Reference: reference,
            Description: description,
            AmountExcl: amount_excl,
            VAT: vat_percentage,
            Unit: unit,
            EAN: ean,
          }),
          partyId: party_id,
          idempotentKey: idempotent_key,
        });
        return typeof result === "object" && result !== null ? result : { ProductID: result };
      }),
  );
}
