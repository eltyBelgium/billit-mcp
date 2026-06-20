"""Order tools — invoices, credit notes, offers, sending, payments.

Billit treats invoice, credit note and offer as one resource discriminated by
``OrderType``. We expose distinct tools per type because LLMs pick them more
reliably and the field requirements differ.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import as_result, drop_none, odata_params, order_id_result

OrderType = Literal["Invoice", "CreditNote", "Offer", "DeliveryNote", "OrderForm"]
OrderDirection = Literal["Income", "Cost"]
TransportType = Literal[
    "SMTP", "Letter", "Peppol", "SDI", "KSeF", "OSA", "ANAF", "SAT", "MyInvois", "Chorus"
]


def register(mcp: FastMCP, client: BillitClient) -> None:
    # ---- reads -----------------------------------------------------------

    @mcp.tool(
        annotations={
            "title": "List orders",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def list_orders(
        order_type: Annotated[
            OrderType | None, Field(description="Filter by document type.")
        ] = None,
        order_direction: Annotated[
            OrderDirection | None,
            Field(description="'Income' for sales (AR) or 'Cost' for purchase (AP)."),
        ] = None,
        search: Annotated[
            str | None,
            Field(description="Free-text search across customer name, number, references."),
        ] = None,
        odata_filter: Annotated[
            str | None,
            Field(description='Raw OData $filter, e.g. "OrderDate gt 2026-01-01".'),
        ] = None,
        top: Annotated[int, Field(ge=1, le=200)] = 50,
        skip: Annotated[int, Field(ge=0)] = 0,
        party_id: Annotated[
            str | None, Field(description="Override the default PartyID for this call.")
        ] = None,
    ) -> dict[str, Any]:
        """List Billit orders (invoices, credit notes, offers, …) for the current PartyID."""
        clauses: list[str] = []
        if order_type:
            clauses.append(f"OrderType eq '{order_type}'")
        if order_direction:
            clauses.append(f"OrderDirection eq '{order_direction}'")
        if odata_filter:
            clauses.append(f"({odata_filter})")
        params = odata_params(
            top=top,
            skip=skip,
            filter_=" and ".join(clauses) or None,
            full_text_search=search,
            orderby="OrderDate desc",
        )
        return await client.get("orders", params=params, party_id=party_id)

    @mcp.tool(annotations={"title": "Get order", "readOnlyHint": True, "openWorldHint": True})
    async def get_order(
        order_id: Annotated[int, Field(description="Integer OrderID returned by list/create.")],
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one order with all lines, attachments, payment status and PDF reference."""
        return await client.get(f"orders/{order_id}", party_id=party_id)

    @mcp.tool(annotations={"title": "List deleted orders", "readOnlyHint": True})
    async def list_deleted_orders(party_id: str | None = None) -> dict[str, Any]:
        """Show orders that have been soft-deleted (still recoverable in Billit UI)."""
        return await client.get("orders/deleted", party_id=party_id)

    # ---- create ----------------------------------------------------------

    @mcp.tool(
        annotations={
            "title": "Create invoice",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    async def create_invoice(
        customer: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Customer payload. Either {'PartyID': 1234} for an existing party, "
                    "or a full party object {'Name': ..., 'VATNumber': ..., 'Email': ..., "
                    "'Addresses': [{'AddressType': 'InvoiceAddress', 'Street': ..., 'City': ..., "
                    "'Zipcode': ..., 'CountryCode': 'BE'}]}."
                )
            ),
        ],
        order_lines: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    "One or more lines: [{'Quantity': 1, 'UnitPriceExcl': 10.0, "
                    "'Description': 'Box of cookies', 'VATPercentage': 21}]"
                )
            ),
        ],
        order_date: Annotated[
            str | None, Field(description="ISO date, e.g. '2026-06-17'. Defaults to today.")
        ] = None,
        expiry_date: Annotated[str | None, Field(description="ISO date for due date.")] = None,
        order_number: Annotated[
            str | None,
            Field(description="Optional; if omitted Billit assigns from your sequence."),
        ] = None,
        currency: Annotated[str, Field(min_length=3, max_length=3)] = "EUR",
        payment_terms: str | None = None,
        attachments: Annotated[
            list[dict[str, Any]] | None,
            Field(description="List of {'FileName', 'FileContent' (base64), 'MimeType'}."),
        ] = None,
        order_pdf: Annotated[
            dict[str, Any] | None,
            Field(description="Inline PDF rendering: {'FileName', 'FileContent', 'MimeType'}."),
        ] = None,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a sales invoice (OrderType=Invoice, OrderDirection=Income).

        Returns the new OrderID. Send it with `send_orders` afterwards.
        """
        body = drop_none(
            {
                "OrderType": "Invoice",
                "OrderDirection": "Income",
                "Customer": customer,
                "OrderLines": order_lines,
                "OrderDate": order_date,
                "ExpiryDate": expiry_date,
                "OrderNumber": order_number,
                "Currency": currency,
                "PaymentTerms": payment_terms,
                "Attachments": attachments,
                "OrderPDF": order_pdf,
            }
        )
        return order_id_result(
            await client.post(
                "orders", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )

    @mcp.tool(
        annotations={
            "title": "Create credit note",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    async def create_credit_note(
        customer: dict[str, Any],
        order_lines: list[dict[str, Any]],
        about_invoice_number: Annotated[
            str | None,
            Field(
                description=(
                    "OrderNumber of the original invoice this credit note refers to. "
                    "Omit if the original was not created in Billit. "
                    "Mutually exclusive with marking the credit note as Paid."
                )
            ),
        ] = None,
        order_date: str | None = None,
        expiry_date: Annotated[
            str | None, Field(description="Required by Billit for credit notes.")
        ] = None,
        currency: str = "EUR",
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a credit note (OrderType=CreditNote, OrderDirection=Income).

        Amounts stay positive in the JSON — only the PDF shows them as negative.
        """
        body = drop_none(
            {
                "OrderType": "CreditNote",
                "OrderDirection": "Income",
                "Customer": customer,
                "OrderLines": order_lines,
                "AboutInvoiceNumber": about_invoice_number,
                "OrderDate": order_date,
                "ExpiryDate": expiry_date,
                "Currency": currency,
            }
        )
        return order_id_result(
            await client.post(
                "orders", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )

    @mcp.tool(
        annotations={
            "title": "Create offer / quote",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    async def create_offer(
        customer: dict[str, Any],
        order_lines: list[dict[str, Any]],
        order_date: str | None = None,
        expiry_date: str | None = None,
        currency: str = "EUR",
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a sales offer / quote (OrderType=Offer, OrderDirection=Income)."""
        body = drop_none(
            {
                "OrderType": "Offer",
                "OrderDirection": "Income",
                "Customer": customer,
                "OrderLines": order_lines,
                "OrderDate": order_date,
                "ExpiryDate": expiry_date,
                "Currency": currency,
            }
        )
        return order_id_result(
            await client.post(
                "orders", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )

    # ---- mutate ----------------------------------------------------------

    @mcp.tool(
        annotations={
            "title": "Update order",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    async def update_order(
        order_id: int,
        patch: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Partial Order object — only the fields you want to change. "
                    "e.g. {'OrderStatus': 'Canceled'} or {'PaymentTerms': '...'}"
                )
            ),
        ],
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """PATCH an order. Use to cancel (set OrderStatus='Canceled'), edit dates, etc."""
        return as_result(
            await client.patch(f"orders/{order_id}", json=patch, party_id=party_id)
        )

    @mcp.tool(
        annotations={
            "title": "Delete order",
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": True,
        }
    )
    async def delete_order(order_id: int, party_id: str | None = None) -> dict[str, Any]:
        """Soft-delete an order. Recoverable via list_deleted_orders."""
        return {
            "deleted_order_id": order_id,
            "result": await client.delete(f"orders/{order_id}", party_id=party_id),
        }

    @mcp.tool(
        annotations={
            "title": "Send orders",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    async def send_orders(
        order_ids: Annotated[list[int], Field(min_length=1, description="OrderIDs to send.")],
        transport_type: Annotated[
            TransportType,
            Field(description="SMTP (email) · Peppol · Letter (physical post) · SDI · KSeF · …"),
        ],
        strict_transport_type: Annotated[
            bool,
            Field(description="If true, disables Billit's fallback to other transports."),
        ] = False,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Send one or more existing orders via the chosen transport.

        All order IDs must belong to the active PartyID. ``Letter`` mails a
        physical paper invoice — production only.
        """
        body = {"OrderIds": order_ids, "TransportType": transport_type}
        extra = {"StrictTransportType": "true"} if strict_transport_type else None
        return as_result(
            await client.post(
                "orders/commands/send",
                json=body,
                party_id=party_id,
                idempotent_key=idempotent_key,
                extra_headers=extra,
            )
        )

    @mcp.tool(
        annotations={
            "title": "Record payment",
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": True,
        }
    )
    async def record_payment(
        order_id: int,
        amount: float,
        payment_date: Annotated[
            str | None, Field(description="ISO date the payment was received.")
        ] = None,
        payment_type: Annotated[
            Literal[
                "Other",
                "Visa",
                "Bancontact",
                "Contant",
                "Wired",
                "Online",
                "Domiciliation",
                "PrivateAccount",
            ]
            | None,
            Field(description="Payment method."),
        ] = None,
        reference: str | None = None,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Attach a payment to an order. Partial payments allowed; the Paid flag
        updates automatically when totals match.
        """
        body = drop_none(
            {
                "Amount": amount,
                "PaymentDate": payment_date,
                "PaymentType": payment_type,
                "Reference": reference,
            }
        )
        return as_result(
            await client.post(
                f"orders/{order_id}/payments",
                json=body,
                party_id=party_id,
                idempotent_key=idempotent_key,
            )
        )
