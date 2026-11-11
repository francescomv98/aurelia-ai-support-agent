import asyncio
import selectors
import uvicorn


async def start_server():
    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())) as runner:
        runner.run(start_server())