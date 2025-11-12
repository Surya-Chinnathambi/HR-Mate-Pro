"""
Uvicorn startup script with proper Windows event loop for psycopg async
"""
import sys
import asyncio
import selectors
import uvicorn

async def main():
    """Main function to run uvicorn with custom event loop"""
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        # Create a selector event loop for Windows + psycopg compatibility
        print("[Startup] Creating SelectorEventLoop for Windows + psycopg async")
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
    else:
        # On Unix, just run normally
        asyncio.run(main())
