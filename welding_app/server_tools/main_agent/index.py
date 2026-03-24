from fastmcp import FastMCP


def register_main_agent_tools(mcp: FastMCP):
    """添加与主agent对话的功能"""

    @mcp.tool()
    def chat_with_main_agent():
        """设计与主agent对话沟通的功能"""
        ...
