from fastmcp import FastMCP

from welding_app.server_tools.file_transfer.index import register_file_transfer_tools

mcp = FastMCP()
register_file_transfer_tools(mcp)


def main():
    mcp.run(transport="sse", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
