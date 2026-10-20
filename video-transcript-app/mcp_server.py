"""Start the transcript MCP server. MCP clients run this file themselves:

    /path/to/video-transcript-app/.venv/bin/python /path/to/video-transcript-app/mcp_server.py

Running it by path puts this folder on Python's import path, so it works from any
working directory. See app/mcp_server.py and the README.
"""

from app.mcp_server import main

if __name__ == "__main__":
    main()
