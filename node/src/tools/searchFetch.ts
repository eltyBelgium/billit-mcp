/**
 * ChatGPT Apps SDK compatibility — `search` and `fetch` with the exact result
 * shapes OpenAI's connectors / Deep Research expect:
 *
 *   search(query) -> { results: [{ id, title, url }] }
 *   fetch(id)     -> { id, title, text, url, metadata? }
 *
 * Both are mapped over Billit orders + parties. Responses include
 * structuredContent plus a JSON text mirror, per the Apps SDK guidance.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { odataParams } from "./util.js";
import { BillitError } from "../errors.js";

const ORDER_PREFIX = "order:";
const PARTY_PREFIX = "party:";

type Rec = Record<string, unknown>;

function items(resp: unknown): Rec[] {
  if (Array.isArray(resp)) return resp as Rec[];
  const inner = (resp as Rec | null)?.Items;
  return Array.isArray(inner) ? (inner as Rec[]) : [];
}

function uiBase(client: BillitClient): string {
  return client.config.baseUrl.replace("api.", "my.");
}

function structured(data: Rec) {
  return {
    structuredContent: data,
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
  };
}

function errorResult(err: unknown) {
  const text =
    err instanceof BillitError
      ? err.toDisplay()
      : err instanceof Error
        ? `${err.name}: ${err.message}`
        : String(err);
  return { isError: true, content: [{ type: "text" as const, text }] };
}

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "search",
    {
      title: "Search Billit",
      description:
        "Search invoices/credit notes/offers and customers/suppliers across Billit. " +
        "Returns result records with ids usable by the fetch tool.",
      inputSchema: { query: z.string().describe("Free-text search query.") },
      outputSchema: {
        results: z.array(
          z.object({ id: z.string(), title: z.string(), url: z.string() }),
        ),
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    async ({ query }) => {
      try {
        const results: { id: string; title: string; url: string }[] = [];

        const orders = await client.get("orders", {
          params: odataParams({ top: 10, fullTextSearch: query, orderby: "OrderDate desc" }),
        });
        for (const o of items(orders)) {
          const oid = o.OrderID ?? o.Id;
          if (oid === undefined || oid === null) continue;
          const customer = (o.Customer as Rec | undefined)?.Name ?? "";
          const title = `${o.OrderType ?? "Order"} ${o.OrderNumber ?? ""} — ${customer}`
            .replace(/ — $/, "")
            .trim();
          results.push({
            id: `${ORDER_PREFIX}${oid}`,
            title: title || `Order ${oid}`,
            url: `${uiBase(client)}/Order/Edit/${oid}`,
          });
        }

        const parties = await client.get("parties", {
          params: odataParams({ top: 10, fullTextSearch: query, orderby: "Name asc" }),
        });
        for (const p of items(parties)) {
          const pid = p.PartyID ?? p.Id;
          if (pid === undefined || pid === null) continue;
          results.push({
            id: `${PARTY_PREFIX}${pid}`,
            title: (p.Name as string) || `Party ${pid}`,
            url: `${uiBase(client)}/Party/Edit/${pid}`,
          });
        }

        return structured({ results });
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.registerTool(
    "fetch",
    {
      title: "Fetch Billit record",
      description: "Fetch a single record by an id returned from the search tool.",
      inputSchema: {
        id: z.string().describe("Record id from search, e.g. 'order:123' or 'party:45'."),
      },
      outputSchema: {
        id: z.string(),
        title: z.string(),
        text: z.string(),
        url: z.string(),
        metadata: z.record(z.string(), z.unknown()).optional(),
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    async ({ id }) => {
      try {
        if (id.startsWith(ORDER_PREFIX)) {
          const oid = id.slice(ORDER_PREFIX.length);
          const order = (await client.get(`orders/${oid}`)) as Rec;
          return structured({
            id,
            title: `${order.OrderType ?? "Order"} ${order.OrderNumber ?? ""}`.trim(),
            text: JSON.stringify(order, null, 2),
            url: `${uiBase(client)}/Order/Edit/${oid}`,
            metadata: {
              type: order.OrderType,
              direction: order.OrderDirection,
              status: order.OrderStatus,
              totalIncl: order.TotalIncl,
              paid: order.Paid,
            },
          });
        }
        if (id.startsWith(PARTY_PREFIX)) {
          const pid = id.slice(PARTY_PREFIX.length);
          const party = (await client.get(`parties/${pid}`)) as Rec;
          return structured({
            id,
            title: (party.Name as string) || `Party ${pid}`,
            text: JSON.stringify(party, null, 2),
            url: `${uiBase(client)}/Party/Edit/${pid}`,
            metadata: {
              type: party.PartyType,
              vat: party.VATNumber,
              email: party.Email,
            },
          });
        }
        return structured({
          id,
          title: "Unknown record",
          text: `Unknown id format '${id}'. Expected '${ORDER_PREFIX}<id>' or '${PARTY_PREFIX}<id>'.`,
          url: "",
        });
      } catch (err) {
        return errorResult(err);
      }
    },
  );
}
