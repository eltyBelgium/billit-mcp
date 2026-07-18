/** Peppol network — participant lookup, inbox, registration. */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { run } from "./util.js";

const partyIdArg = z.string().optional().describe("Override the default PartyID for this call.");

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "lookup_peppol_participant",
    {
      title: "Lookup Peppol participant",
      description:
        "Check whether a company is registered on the Peppol network. Useful as a " +
        "pre-flight check before sending via Peppol. This Billit endpoint needs no auth.",
      inputSchema: {
        vat_or_cbe: z
          .string()
          .describe("VAT number (e.g. 'BE0563846944') or Belgian CBE/KBO number."),
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ vat_or_cbe }) =>
      run(() => client.get(`peppol/participantInformation/${encodeURIComponent(vat_or_cbe)}`)),
  );

  server.registerTool(
    "list_peppol_inbox",
    {
      title: "List Peppol inbox",
      description: "Show inbound Peppol documents (returns first 10 items).",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_id }) => run(() => client.get("peppol/inbox", { partyId: party_id })),
  );

  server.registerTool(
    "confirm_peppol_inbox",
    {
      title: "Accept Peppol document",
      description: "Accept an inbound Peppol document into your Billit inbox.",
      inputSchema: { inbox_item_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ inbox_item_id, party_id }) =>
      run(async () => ({
        inbox_item_id,
        result: await client.post(`peppol/inbox/${inbox_item_id}/confirm`, {
          partyId: party_id,
        }),
      })),
  );

  server.registerTool(
    "refuse_peppol_inbox",
    {
      title: "Refuse Peppol document",
      description: "Reject an inbound Peppol document.",
      inputSchema: { inbox_item_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    },
    ({ inbox_item_id, party_id }) =>
      run(async () => ({
        inbox_item_id,
        result: await client.post(`peppol/inbox/${inbox_item_id}/refuse`, {
          partyId: party_id,
        }),
      })),
  );

  server.registerTool(
    "register_peppol_participant",
    {
      title: "Register on Peppol",
      description: "Register the current company on the Peppol network.",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ party_id }) =>
      run(async () => ({
        result: await client.post("peppol/participants", { partyId: party_id }),
      })),
  );
}
