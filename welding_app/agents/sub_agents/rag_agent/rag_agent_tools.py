from pathlib import Path

from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from welding_app.error.error_message import ToolErrorCode, ToolException

from .types import RetrieverInput, RetrieverOutput

_rag_database_path = (
    Path(__file__).parent.parent.parent.parent
    / "databases"
    / "rag_data"
    / "chroma_langchain_db"
)

_vector_store = None


def _init_rag_database():
    global _vector_store
    if _vector_store is not None:  # 已初始化直接返回
        return _vector_store

    embedding_model = OllamaEmbeddings(model="nomic-embed-text")
    _vector_store = Chroma(
        collection_name="example_collection",
        embedding_function=embedding_model,
        persist_directory=str(_rag_database_path),
    )
    return _vector_store


@tool(
    args_schema=RetrieverInput,
    description=f"""焊接知识检索工具
    输入关键词或者关键的语句，本工具会调用内置的知识库进行检索，返回检索到的结果。

    Returns:
        RetrieverOutput:
            <json-schema>
                {RetrieverOutput.model_json_schema()}
            </json-schema>

    Error: 可能会报错
    """,
)
def retriever(query: str, res_len: int):
    try:
        _vector_store = _init_rag_database()
    except Exception as e:
        raise ToolException(
            message=str(e),
            code=ToolErrorCode.UNKNOWN,
            details="可能是ollama未成功配置，也可能是数据库位置错误",
            input_args=RetrieverInput(query=query, res_len=res_len).model_dump(),
            content="初始化向量数据库失败",
            tool_name="retriever",
            retryable=False,
        )

    try:
        results = _vector_store.similarity_search(query, k=res_len)
        return RetrieverOutput(results=[r.page_content for r in results])
    except Exception as e:
        raise ToolException(
            message=str(e),
            code=ToolErrorCode.UNKNOWN,
            details=None,
            input_args=RetrieverInput(query=query, res_len=res_len).model_dump(),
            content="在检索阶段发生错误",
            tool_name="retriever",
            retryable=False,
        )


if __name__ == "__main__":
    vector_store = _init_rag_database()
    ans = vector_store.similarity_search("电流如何设置")
    print(ans)
