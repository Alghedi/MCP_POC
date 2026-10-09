import logging
import ssl

import httpx
import truststore
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.core.auth import token_verifier
from app.core.config import settings

mcp = FastMCP(name="MCP Server", auth=token_verifier)

# Trust the OS certificate store (needed behind TLS-intercepting corporate proxies)
_ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.tool
async def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
) -> dict:
    """Use this to get current exchange rates.

    Args:
        currency_from (str): The base currency code (default is "USD").
        currency_to (str): The target currency code (default is "EUR").
        currency_date (str): The date for the exchange rate, or "latest" for the most recent rate (default is "latest").
    """
    logging.info(f"Fetching exchange rate from {currency_from} to {currency_to} for date {currency_date}")
    try:
        async with httpx.AsyncClient(verify=_ssl_context) as client:
            response = await client.get(
                f"https://api.frankfurter.dev/v1/{currency_date}",
                params={"from": currency_from, "to": currency_to},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:  # Handle HTTP/network errors
        logging.error(f"HTTP error occurred: {e}")
        return {"error": str(e)}
    except ValueError as e:  # Handle invalid JSON responses
        logging.error(f"Value error occurred: {e}")
        return {"error": str(e)}

    if "rates" not in data:
        return {"error": "Rates not found in response"}
    return data

if __name__ == "__main__":
    mcp.run(transport="http", host=settings.MCP_HOST, port=settings.MCP_PORT)
