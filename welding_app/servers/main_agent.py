from fastmcp import FastMCP

from welding_app.server_tools.main_agent.index import register_main_agent_tools

mcp = FastMCP()
register_main_agent_tools(mcp)


def main():
    mcp.run(transport="sse", host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
