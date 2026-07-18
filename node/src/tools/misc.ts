/** Reports, inbound OCR queue, and account info. */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { dropNone, run } from "./util.js";

const partyIdArg = z.string().optional().describe("Override the default PartyID for this call.");

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "list_reports",
    {
      title: "List reports",
      description: "List available report definitions for the current PartyID.",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_id }) =>
      run(async () => {
        const result = await client.get("reports", { partyId: party_id });
        return Array.isArray(result) ? { items: result } : result;
      }),
  );

  server.registerTool(
    "get_report",
    {
      title: "Get report",
      description: "Fetch a report's generated CSV results.",
      inputSchema: { report_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ report_id, party_id }) =>
      run(() => client.get(`reports/${report_id}`, { partyId: party_id })),
  );

  server.registerTool(
    "submit_inbound_pdf",
    {
      title: "Submit inbound PDF for OCR",
      description:
        "Upload a supplier invoice PDF. Billit OCRs it and surfaces it as a Cost order.",
      inputSchema: {
        file_name: z.string(),
        file_content_base64: z.string().describe("Base64-encoded PDF bytes."),
        mime_type: z.string().default("application/pdf"),
        idempotent_key: z.string().optional(),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ file_name, file_content_base64, mime_type, idempotent_key, party_id }) =>
      run(async () => ({
        result: await client.post("toProcess", {
          body: dropNone({
            File: { FileName: file_name, FileContent: file_content_base64, MimeType: mime_type },
          }),
          partyId: party_id,
          idempotentKey: idempotent_key,
        }),
      })),
  );

  server.registerTool(
    "list_inbound_queue",
    {
      title: "List inbound queue",
      description: "Show items currently in the OCR/inbound queue.",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_id }) =>
      run(async () => {
        const result = await client.get("toProcess", { partyId: party_id });
        return Array.isArray(result) ? { items: result } : result;
      }),
  );

  server.registerTool(
    "get_account_info",
    {
      title: "Get account info",
      description:
        "Return current company info, license, addons and sequences. Useful as a " +
        "connectivity smoke test — a 200 means apikey + partyID are valid for this base URL.",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_id }) =>
      run(() => client.get("account/accountInformation", { partyId: party_id })),
  );
}
