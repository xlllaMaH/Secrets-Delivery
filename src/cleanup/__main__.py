import asyncio

from src.cleanup.service import run_cleanup
from src.database import async_session_maker, engine


async def main() -> None:
    async with async_session_maker() as db:
        stats = await run_cleanup(db)
    await engine.dispose()
    print(f"wiped notes: {stats.notes}, deleted refresh tokens: {stats.tokens}")


if __name__ == "__main__":
    asyncio.run(main())
