/** Document storage + binary file download. */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { dropNone, odataParams, run } from "./util.js";

const partyIdArg = z.string().optional().describe("Override the default PartyID for this call.");

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "list_documents",
    {
      title: "List documents",
      description: "List documents stored against the current PartyID.",
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
        client.get("documents", {
          params: odataParams({ top, skip, fullTextSearch: search }),
          partyId: party_id,
        }),
      ),
  );

  server.registerTool(
    "get_document",
    {
      title: "Get document",
      description: "Fetch one document's metadata + file references.",
      inputSchema: { document_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ document_id, party_id }) =>
      run(() => client.get(`documents/${document_id}`, { partyId: party_id })),
  );

  server.registerTool(
    "upload_document",
    {
      title: "Upload document",
      description: "Upload a document (inline base64). Returns the new DocumentID.",
      inputSchema: {
        name: z.string(),
        file_content_base64: z.string().describe("Base64-encoded file bytes."),
        mime_type: z.string().default("application/pdf"),
        description: z.string().optional(),
        document_date: z.string().optional(),
        tags: z.array(z.string()).optional(),
        idempotent_key: z.string().optional(),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    (args) =>
      run(async () => {
        const result = await client.post("documents", {
          body: dropNone({
            Name: args.name,
            Description: args.description,
            DocumentDate: args.document_date,
            Tags: args.tags,
            File: {
              FileName: args.name,
              FileContent: args.file_content_base64,
              MimeType: args.mime_type,
            },
          }),
          partyId: args.party_id,
          idempotentKey: args.idempotent_key,
        });
        return typeof result === "object" && result !== null ? result : { DocumentID: result };
      }),
  );

  server.registerTool(
    "download_file",
    {
      title: "Download file",
      description:
        "Download a file by its UUID (typically Order.OrderPDF.FileID). Returns base64 " +
        "content plus content type and size.",
      inputSchema: {
        file_id: z.string().describe("File UUID from Order.OrderPDF.FileID or attachments."),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ file_id, party_id }) =>
      run(async () => {
        const file = await client.getBinary(`files/${file_id}`, { partyId: party_id });
        return { file_id, content_type: file.contentType, bytes: file.bytes, base64: file.base64 };
      }),
  );
}
