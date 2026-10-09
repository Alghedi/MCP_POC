import argparse
import asyncio

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from app.core.config import settings


async def _login() -> str:
    if not settings.MCP_CLIENT_EMAIL or not settings.MCP_CLIENT_PASSWORD:
        raise RuntimeError(
            "Configura MCP_CLIENT_EMAIL y MCP_CLIENT_PASSWORD en .env antes de usar el cliente"
        )

    async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL) as client:
        response = await client.post(
            "/auth/login",
            json={"email": settings.MCP_CLIENT_EMAIL, "password": settings.MCP_CLIENT_PASSWORD},
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_exchange_rate(currency_from: str, currency_to: str, currency_date: str) -> None:
    access_token = await _login()
    transport = StreamableHttpTransport(
        settings.MCP_SERVER_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "get_exchange_rate",
            {
                "currency_from": currency_from,
                "currency_to": currency_to,
                "currency_date": currency_date,
            },
        )
        print(result.data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cliente MCP: consulta tipos de cambio")
    parser.add_argument("--from", dest="currency_from", default="USD", help="Moneda origen (default: USD)")
    parser.add_argument("--to", dest="currency_to", default="EUR", help="Moneda destino (default: EUR)")
    parser.add_argument("--date", dest="currency_date", default="latest", help="Fecha o 'latest' (default: latest)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(get_exchange_rate(args.currency_from, args.currency_to, args.currency_date))
