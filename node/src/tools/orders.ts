/**
 * Order tools — invoices, credit notes, offers, sending, payments.
 *
 * Billit treats invoice / credit note / offer as one resource discriminated by
 * OrderType. We expose distinct create tools per type because models pick them
 * more reliably and the field requirements differ.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import type { BillitClient } from "../client.js";
import { dropNone, odataParams, run } from "./util.js";

const ORDER_TYPES = ["Invoice", "CreditNote", "Offer", "DeliveryNote", "OrderForm"] as const;
const DIRECTIONS = ["Income", "Cost"] as const;
const TRANSPORTS = [
  "SMTP",
  "Letter",
  "Peppol",
  "SDI",
  "KSeF",
  "OSA",
  "ANAF",
  "SAT",
  "MyInvois",
  "Chorus",
] as const;
const PAYMENT_TYPES = [
  "Other",
  "Visa",
  "Bancontact",
  "Contant",
  "Wired",
  "Online",
  "Domiciliation",
  "PrivateAccount",
] as const;

const partyIdArg = z
  .string()
  .optional()
  .describe("Override the default PartyID (company context) for this call.");
const idempotentKeyArg = z
  .string()
  .optional()
  .describe("Client-side dedupe key for safe retries. Auto-generated UUID if omitted.");

const customerArg = z
  .record(z.string(), z.unknown())
  .describe(
    "Customer payload. Either {'PartyID': 1234} for an existing party, or a full party " +
      "object {'Name': ..., 'VATNumber': ..., 'Email': ..., 'Addresses': [{'AddressType': " +
      "'InvoiceAddress', 'Street': ..., 'City': ..., 'Zipcode': ..., 'CountryCode': 'BE'}]}.",
  );
const orderLinesArg = z
  .array(z.record(z.string(), z.unknown()))
  .min(1)
  .describe(
    "One or more lines: [{'Quantity': 1, 'UnitPriceExcl': 10.0, 'Description': " +
      "'Box of cookies', 'VATPercentage': 21}]",
  );

export function register(server: McpServer, client: BillitClient): void {
  server.registerTool(
    "list_orders",
    {
      title: "List orders",
      description:
        "List Billit orders (invoices, credit notes, offers, …) for the current PartyID.",
      inputSchema: {
        order_type: z.enum(ORDER_TYPES).optional().describe("Filter by document type."),
        order_direction: z
          .enum(DIRECTIONS)
          .optional()
          .describe("'Income' for sales (AR) or 'Cost' for purchase (AP)."),
        search: z
          .string()
          .optional()
          .describe("Free-text search across customer name, number, references."),
        odata_filter: z
          .string()
          .optional()
          .describe("Raw OData $filter, e.g. \"OrderDate gt 2026-01-01\"."),
        top: z.number().int().min(1).max(200).default(50),
        skip: z.number().int().min(0).default(0),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ order_type, order_direction, search, odata_filter, top, skip, party_id }) =>
      run(() => {
        const clauses: string[] = [];
        if (order_type) clauses.push(`OrderType eq '${order_type}'`);
        if (order_direction) clauses.push(`OrderDirection eq '${order_direction}'`);
        if (odata_filter) clauses.push(`(${odata_filter})`);
        return client.get("orders", {
          params: odataParams({
            top,
            skip,
            filter: clauses.join(" and "),
            fullTextSearch: search,
            orderby: "OrderDate desc",
          }),
          partyId: party_id,
        });
      }),
  );

  server.registerTool(
    "get_order",
    {
      title: "Get order",
      description:
        "Fetch one order with all lines, attachments, payment status and PDF reference.",
      inputSchema: {
        order_id: z.number().int().describe("Integer OrderID returned by list/create."),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ order_id, party_id }) => run(() => client.get(`orders/${order_id}`, { partyId: party_id })),
  );

  server.registerTool(
    "list_deleted_orders",
    {
      title: "List deleted orders",
      description: "Show orders that have been soft-deleted (still recoverable in Billit UI).",
      inputSchema: { party_id: partyIdArg },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    ({ party_id }) => run(() => client.get("orders/deleted", { partyId: party_id })),
  );

  server.registerTool(
    "create_invoice",
    {
      title: "Create invoice",
      description:
        "Create a sales invoice (OrderType=Invoice, OrderDirection=Income). Returns the new " +
        "OrderID. Send it afterwards with send_orders.",
      inputSchema: {
        customer: customerArg,
        order_lines: orderLinesArg,
        order_date: z.string().optional().describe("ISO date, e.g. '2026-07-18'. Defaults to today."),
        expiry_date: z.string().optional().describe("ISO due date."),
        order_number: z
          .string()
          .optional()
          .describe("Optional; if omitted Billit assigns from your sequence."),
        currency: z.string().length(3).default("EUR"),
        payment_terms: z.string().optional(),
        attachments: z
          .array(z.record(z.string(), z.unknown()))
          .optional()
          .describe("List of {'FileName', 'FileContent' (base64), 'MimeType'}."),
        order_pdf: z
          .record(z.string(), z.unknown())
          .optional()
          .describe("Inline PDF rendering: {'FileName', 'FileContent', 'MimeType'}."),
        idempotent_key: idempotentKeyArg,
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    (args) =>
      run(async () => {
        const result = await client.post("orders", {
          body: dropNone({
            OrderType: "Invoice",
            OrderDirection: "Income",
            Customer: args.customer,
            OrderLines: args.order_lines,
            OrderDate: args.order_date,
            ExpiryDate: args.expiry_date,
            OrderNumber: args.order_number,
            Currency: args.currency,
            PaymentTerms: args.payment_terms,
            Attachments: args.attachments,
            OrderPDF: args.order_pdf,
          }),
          partyId: args.party_id,
          idempotentKey: args.idempotent_key,
        });
        // Billit returns a bare int OrderID.
        return typeof result === "object" && result !== null ? result : { OrderID: result };
      }),
  );

  server.registerTool(
    "create_credit_note",
    {
      title: "Create credit note",
      description:
        "Create a credit note (OrderType=CreditNote, OrderDirection=Income). Amounts stay " +
        "positive in the JSON — only the PDF shows them as negative.",
      inputSchema: {
        customer: customerArg,
        order_lines: orderLinesArg,
        about_invoice_number: z
          .string()
          .optional()
          .describe(
            "OrderNumber of the original invoice this credit note refers to. Omit if the " +
              "original was not created in Billit. Mutually exclusive with marking it Paid.",
          ),
        order_date: z.string().optional(),
        expiry_date: z.string().optional().describe("Required by Billit for credit notes."),
        currency: z.string().length(3).default("EUR"),
        idempotent_key: idempotentKeyArg,
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    (args) =>
      run(async () => {
        const result = await client.post("orders", {
          body: dropNone({
            OrderType: "CreditNote",
            OrderDirection: "Income",
            Customer: args.customer,
            OrderLines: args.order_lines,
            AboutInvoiceNumber: args.about_invoice_number,
            OrderDate: args.order_date,
            ExpiryDate: args.expiry_date,
            Currency: args.currency,
          }),
          partyId: args.party_id,
          idempotentKey: args.idempotent_key,
        });
        return typeof result === "object" && result !== null ? result : { OrderID: result };
      }),
  );

  server.registerTool(
    "create_offer",
    {
      title: "Create offer / quote",
      description: "Create a sales offer / quote (OrderType=Offer, OrderDirection=Income).",
      inputSchema: {
        customer: customerArg,
        order_lines: orderLinesArg,
        order_date: z.string().optional(),
        expiry_date: z.string().optional(),
        currency: z.string().length(3).default("EUR"),
        idempotent_key: idempotentKeyArg,
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    (args) =>
      run(async () => {
        const result = await client.post("orders", {
          body: dropNone({
            OrderType: "Offer",
            OrderDirection: "Income",
            Customer: args.customer,
            OrderLines: args.order_lines,
            OrderDate: args.order_date,
            ExpiryDate: args.expiry_date,
            Currency: args.currency,
          }),
          partyId: args.party_id,
          idempotentKey: args.idempotent_key,
        });
        return typeof result === "object" && result !== null ? result : { OrderID: result };
      }),
  );

  server.registerTool(
    "update_order",
    {
      title: "Update order",
      description:
        "PATCH an order. Use to cancel (set OrderStatus='Canceled'), edit dates, etc.",
      inputSchema: {
        order_id: z.number().int(),
        patch: z
          .record(z.string(), z.unknown())
          .describe(
            "Partial Order object — only fields you want to change, e.g. " +
              "{'OrderStatus': 'Canceled'}.",
          ),
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ order_id, patch, party_id }) =>
      run(async () => {
        const result = await client.patch(`orders/${order_id}`, {
          body: patch,
          partyId: party_id,
        });
        return { order_id, result };
      }),
  );

  server.registerTool(
    "delete_order",
    {
      title: "Delete order",
      description: "Soft-delete an order. Recoverable via list_deleted_orders.",
      inputSchema: { order_id: z.number().int(), party_id: partyIdArg },
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    },
    ({ order_id, party_id }) =>
      run(async () => ({
        deleted_order_id: order_id,
        result: await client.delete(`orders/${order_id}`, { partyId: party_id }),
      })),
  );

  server.registerTool(
    "send_orders",
    {
      title: "Send orders",
      description:
        "Send existing orders via a transport. All OrderIDs must belong to the active " +
        "PartyID. 'Letter' mails a physical paper invoice — production only.",
      inputSchema: {
        order_ids: z.array(z.number().int()).min(1).describe("OrderIDs to send."),
        transport_type: z
          .enum(TRANSPORTS)
          .describe("SMTP (email) · Peppol · Letter (physical post) · SDI · KSeF · …"),
        strict_transport_type: z
          .boolean()
          .default(false)
          .describe("If true, disables Billit's fallback to other transports."),
        idempotent_key: idempotentKeyArg,
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ order_ids, transport_type, strict_transport_type, idempotent_key, party_id }) =>
      run(async () => {
        const result = await client.post("orders/commands/send", {
          body: { OrderIds: order_ids, TransportType: transport_type },
          partyId: party_id,
          idempotentKey: idempotent_key,
          extraHeaders: strict_transport_type ? { StrictTransportType: "true" } : undefined,
        });
        return { sent_order_ids: order_ids, transport: transport_type, result };
      }),
  );

  server.registerTool(
    "record_payment",
    {
      title: "Record payment",
      description:
        "Attach a payment to an order. Partial payments allowed; the Paid flag updates " +
        "automatically when totals match.",
      inputSchema: {
        order_id: z.number().int(),
        amount: z.number(),
        payment_date: z.string().optional().describe("ISO date the payment was received."),
        payment_type: z.enum(PAYMENT_TYPES).optional(),
        reference: z.string().optional(),
        idempotent_key: idempotentKeyArg,
        party_id: partyIdArg,
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    },
    ({ order_id, amount, payment_date, payment_type, reference, idempotent_key, party_id }) =>
      run(async () => {
        const result = await client.post(`orders/${order_id}/payments`, {
          body: dropNone({
            Amount: amount,
            PaymentDate: payment_date,
            PaymentType: payment_type,
            Reference: reference,
          }),
          partyId: party_id,
          idempotentKey: idempotent_key,
        });
        return { order_id, amount, result };
      }),
  );
}
