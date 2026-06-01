"""Entry point for the Holders cron job on Render."""
import asyncio
from daily_holdings_worker import main

if __name__ == "__main__":
    asyncio.run(main())
