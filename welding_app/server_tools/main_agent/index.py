from typing import Annotated

from fastmcp import FastMCP
from langchain.messages import HumanMessage
from pydantic import Field

from welding_app.agents.main_agent import create_main_agent
from welding_app.server_types.main_agent_responce import MainAgentResponse


def register_main_agent_tools(mcp: FastMCP):
    """添加与主agent对话的功能"""

    main_agent = create_main_agent()

    @mcp.tool(
        description=f"""与焊接工艺设计系统的主agent对话，分派任务
        Returns:
            MainAgentResponse: <json-schema>{MainAgentResponse.model_json_schema()}</json-schema>
        """
    )
    def chat_with_main_agent(
        message: Annotated[
            str,
            Field(
                description="""此项参数用于与主agent的对话，输入你要与主agent交流的内容"""
            ),
        ],
        thread_id: Annotated[
            int,
            Field(
                description="""此项参数用于指定对话的线程ID
                <explain>由于主agent会承担很长的上下文，对于两个独立的任务，你应该为他设置单独的thread_id</explain>"""
            ),
        ],
    ) -> MainAgentResponse:
        """设计与主agent对话沟通的功能"""
        res = main_agent.invoke(
            input={"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        return MainAgentResponse(
            message=res["messages"][-1].content, thread_id=thread_id
        )
