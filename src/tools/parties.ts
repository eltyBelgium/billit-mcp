/** Party tools — customers and suppliers. */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { dropNone, odataParams, run } from "./util.js";

const partyIdArg = z
  .string()
  .optional()
  .describe("Override the default PartyID (company context) for this call.");

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "list_parties",
    {
      title: "List parties",
      description: "List customers and/or suppliers.",
      inputSchema: {
        party_type: z.enum(["Customer", "Supplier"]).optional(),
        search: z.string().optional().describe("Free-text search across name, VAT, email."),
        top: z.number().int().min(1).max(200).default(50),
        skip: z.number().int().min(0).default(0),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_type, search, top, skip, party_id }) =>
      run(() =>
        client.get("parties", {
          params: odataParams({
            top,
            skip,
            filter: party_type ? `PartyType eq '${party_type}'` : undefined,
            fullTextSearch: search,
            orderby: "Name asc",
          }),
          partyId: party_id,
        }),
      ),
  );

  server.registerTool(
    "get_party",
    {
      title: "Get party",
      description:
        "Fetch one party by its resource ID. (Different integer than the company PartyID " +
        "header.)",
      inputSchema: { target_party_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ target_party_id, party_id }) =>
      run(() => client.get(`parties/${target_party_id}`, { partyId: party_id })),
  );

  server.registerTool(
    "find_party_by_vat",
    {
      title: "Find party by VAT",
      description: "Look up a party by VAT number. Returns matches (usually 0 or 1).",
      inputSchema: {
        vat_number: z
          .string()
          .describe("VAT number with country prefix, e.g. 'BE0563846944'."),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ vat_number, party_id }) =>
      run(() =>
        client.get("parties", {
          params: odataParams({ filter: `VATNumber eq '${vat_number}'`, top: 5 }),
          partyId: party_id,
        }),
      ),
  );

  server.registerTool(
    "create_party",
    {
      title: "Create or upsert party",
      description:
        "Create a customer or supplier. Billit will upsert by VATNumber where possible.",
      inputSchema: {
        name: z.string(),
        party_type: z.enum(["Customer", "Supplier"]),
        vat_number: z.string().optional(),
        email: z.string().optional(),
        phone: z.string().optional(),
        iban: z.string().optional(),
        addresses: z
          .array(z.record(z.string(), z.unknown()))
          .optional()
          .describe(
            "Each {'AddressType': 'InvoiceAddress'|'DeliveryAddress', 'Street': ..., " +
              "'City': ..., 'Zipcode': ..., 'CountryCode': 'BE'}",
          ),
        idempotent_key: z.string().optional(),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, idempotentHint: true, openWorldHint: true },
    },
    ({ name, party_type, vat_number, email, phone, iban, addresses, idempotent_key, party_id }) =>
      run(async () => {
        const result = await client.post("parties", {
          body: dropNone({
            Name: name,
            PartyType: party_type,
            VATNumber: vat_number,
            Email: email,
            Phone: phone,
            IBAN: iban,
            Addresses: addresses,
          }),
          partyId: party_id,
          idempotentKey: idempotent_key,
        });
        return typeof result === "object" && result !== null ? result : { PartyID: result };
      }),
  );

  server.registerTool(
    "update_party",
    {
      title: "Update party",
      description: "PATCH a party. Pass only the fields you want to change.",
      inputSchema: {
        target_party_id: z.number().int(),
        patch: z.record(z.string(), z.unknown()),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ target_party_id, patch, party_id }) =>
      run(async () => ({
        target_party_id,
        result: await client.patch(`parties/${target_party_id}`, {
          body: patch,
          partyId: party_id,
        }),
      })),
  );
}
