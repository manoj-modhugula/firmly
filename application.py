"""Firmly ASGI entry point."""

from firmly_api.app import create_app

app = create_app()
api = app.state.api

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
