from pydantic import BaseModel, Field


class MainAgentResponse(BaseModel):
    message: str = Field(description="""主agent返回的消息内容""")
    thread_id: int = Field(description="""主agent返回的线程ID""")
