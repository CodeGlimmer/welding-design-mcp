"""
最小化测试：验证 ChatOpenAI + DeepSeek V4 thinking mode + tool calling 兼容性

用法：在项目根目录下运行
    python -m welding_app.test_thinking_tool
"""

import os

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

from welding_app.agents.runtime_config import agent_config


def get_current_time() -> str:
    """获取当前时间（模拟工具）"""
    from datetime import datetime

    print("被调用了")

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def test_with_chatopenai():
    """测试 ChatOpenAI + deepseek-v4-pro + thinking mode + tool calling"""
    print("=" * 60)
    print("测试: ChatOpenAI + deepseek-v4-pro + thinking + tool")
    print("=" * 60)

    model = ChatOpenAI(
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/beta",
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。当用户询问时间时，使用 get_current_time 工具。",
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content="现在几点了？请用中文回答。")]},
            agent_config(thread_id="test-chatopenai"),
        )
        print("✅ 成功！响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_with_chatdeepseek():
    """测试 ChatDeepSeek + deepseek-v4-pro + thinking mode + tool calling（对照组）"""
    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + deepseek-v4-pro + thinking + tool")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。当用户询问时间时，使用 get_current_time 工具。",
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content="现在几点了？请用中文回答。")]},
            agent_config(thread_id="test-chatdeepseek"),
        )
        print("✅ 成功！响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_tool_strategy():
    """测试 ChatDeepSeek + ToolStrategy（结构化输出） + thinking mode"""
    from langchain.agents.structured_output import ToolStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + ToolStrategy + thinking + tool")
    print("（此测试会触发 tool_choice='any'）")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=ToolStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-toolstrategy"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        print("消息响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_provider_strategy():
    """测试 ChatDeepSeek + ProviderStrategy + thinking mode"""
    from langchain.agents.structured_output import ProviderStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + ProviderStrategy + thinking + tool")
    print("（使用 OpenAI 原生 structured output）")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=ProviderStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-providerstrategy"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_auto_strategy():
    """测试 ChatDeepSeek + AutoStrategy + thinking mode"""
    from langchain.agents.structured_output import AutoStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + AutoStrategy + thinking + tool")
    print("（自动选择最优策略）")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=AutoStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-autostrategy"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_strategy():
    """测试 ChatDeepSeek + 普通 response_format（Pydantic schema 直传）+ thinking mode"""
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + Pydantic schema 直传 + thinking + tool")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=WeatherResult,
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-nostrategy"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_json_object_response_format():
    """测试 response_format={'type': 'json_object'} + thinking mode（无工具）"""
    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + json_object + thinking（无工具）")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    agent = create_agent(
        model=model,
        system_prompt='你是一个有用的助手。请始终以 JSON 格式输出，格式为：{"time": "...", "message": "..."}',
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(content="现在几点了？用 JSON 回答，时间可以随便编。")
                ]
            },
            agent_config(thread_id="test-jsonobject"),
        )
        print("✅ 成功！响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_json_object_with_tool():
    """测试 response_format={'type': 'json_object'} + thinking + tool（需工具兼容 strict）"""
    from langchain_core.tools import tool

    @tool(response_format="content")
    def get_time_strict() -> str:
        """获取当前时间"""
        from datetime import datetime

        print("被调用了(strict)")
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek + json_object + thinking + strict tool")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_time_strict],
        system_prompt='你是一个有用的助手。当用户询问时间时，使用 get_time_strict 工具，并以 JSON 格式输出：{"time": "...", "message": "..."}',
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content="现在几点了？用 JSON 回答。")]},
            agent_config(thread_id="test-jsonobject-tool"),
        )
        print("✅ 成功！响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_model_with_structured_output():
    """测试 model.with_structured_output(method='json_mode') + thinking mode"""
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")

    print("\n" + "=" * 60)
    print("测试: ChatDeepSeek.with_structured_output(json_mode) + thinking")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    base_model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    # 用 with_structured_output 包装，method='json_mode' 使用 json_object
    model = base_model.with_structured_output(WeatherResult, method="json_mode")

    try:
        # prompt 必须包含 'json' 关键字
        result = model.invoke(
            "查询杭州的天气，用 JSON 格式返回。时间用当前时间，温度随便编一个。"
        )
        print("✅ 成功！结构化响应：")
        print(result)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_thinking_tool_strategy():
    """对照组：非thinking模式 + ToolStrategy"""
    from langchain.agents.structured_output import ToolStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("对照组: 非thinking + ToolStrategy")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=ToolStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-no-think-tool"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        print("消息响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_thinking_provider_strategy():
    """对照组：非thinking模式 + ProviderStrategy"""
    from langchain.agents.structured_output import ProviderStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("对照组: 非thinking + ProviderStrategy")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=ProviderStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-no-think-provider"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_thinking_auto_strategy():
    """对照组：非thinking模式 + AutoStrategy"""
    from langchain.agents.structured_output import AutoStrategy
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("对照组: 非thinking + AutoStrategy")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=AutoStrategy(WeatherResult),
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-no-think-auto"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_thinking_pydantic():
    """对照组：非thinking模式 + Pydantic直传"""
    from pydantic import BaseModel, Field

    class WeatherResult(BaseModel):
        """天气查询结果"""

        location: str = Field(description="城市名")
        temperature: str = Field(description="温度")
        summary: str = Field(description="天气总结")

    print("\n" + "=" * 60)
    print("对照组: 非thinking + Pydantic直传")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。",
        response_format=WeatherResult,
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的时间和天气（用 get_current_time 获取时间，天气随便编一个）。"
                    )
                ]
            },
            agent_config(thread_id="test-no-think-pydantic"),
        )
        print("✅ 成功！结构化响应：")
        print(result.get("structured_response"))
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_no_thinking_normal_tool():
    """对照组：非thinking模式 + 普通工具（无结构化输出）"""
    print("\n" + "=" * 60)
    print("对照组: 非thinking + 普通工具")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="你是一个有用的助手。当用户询问时间时，使用 get_current_time 工具。",
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content="现在几点了？请用中文回答。")]},
            agent_config(thread_id="test-no-think-normal"),
        )
        print("✅ 成功！响应：")
        print(result["messages"][-1].content)
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_prompt_schema_with_tools():
    """测试 thinking + 工具 + prompt 内嵌 schema（不用 ToolStrategy）"""
    import json

    print("\n" + "=" * 60)
    print("测试: thinking + 工具 + prompt 内嵌 JSON schema")
    print("（不用 ToolStrategy，schema 写提示词里）")
    print("=" * 60)

    from langchain_deepseek import ChatDeepSeek

    schema_hint = """
输出格式要求：你必须以 JSON 格式输出最终结果，格式如下：
{
    "location": "城市名",
    "time": "时间",
    "temperature": "温度",
    "summary": "天气总结"
}
"""

    model = ChatDeepSeek(
        model="deepseek-v4-pro",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )

    agent = create_agent(
        model=model,
        tools=[get_current_time],
        system_prompt=f"你是一个有用的助手。使用 get_current_time 获取时间。{schema_hint}",
    )

    try:
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="查询杭州现在的天气和时间（用 get_current_time 获取时间，天气和温度随便编）。请按 JSON 格式输出。"
                    )
                ]
            },
            agent_config(thread_id="test-prompt-schema"),
        )
        content = result["messages"][-1].content
        print("✅ 成功！原始响应：")
        print(content)
        # 尝试解析 JSON
        try:
            parsed = json.loads(content)
            print("✅ JSON 解析成功：")
            print(parsed)
        except json.JSONDecodeError:
            print("⚠️ 返回内容不是纯 JSON（可能需要提取）")
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("【实验组：thinking 模式】")
    print("=" * 60)
    success_openai = test_with_chatopenai()
    success_deepseek = test_with_chatdeepseek()
    success_tool = test_tool_strategy()
    success_provider = test_provider_strategy()
    success_auto = test_auto_strategy()
    success_none = test_no_strategy()
    success_json = test_json_object_response_format()
    success_json_tool = test_json_object_with_tool()
    success_with = test_model_with_structured_output()
    success_prompt_schema = test_prompt_schema_with_tools()

    print("\n" + "=" * 60)
    print("【对照组：显式关闭 thinking (type=disabled)】")
    print("=" * 60)
    success_no_think_normal = test_no_thinking_normal_tool()
    success_no_think_tool = test_no_thinking_tool_strategy()
    success_no_think_provider = test_no_thinking_provider_strategy()
    success_no_think_auto = test_no_thinking_auto_strategy()
    success_no_think_pydantic = test_no_thinking_pydantic()

    print("\n" + "=" * 60)
    print("结果汇总：")
    print("=" * 60)
    print("【thinking 模式】")
    print(f"  普通工具:               {'✅' if success_deepseek else '❌'}")
    print(
        f"  ToolStrategy:           {'✅' if success_tool else '❌ — tool_choice=any 不兼容'}"
    )
    print(f"  ProviderStrategy:       {'✅' if success_provider else '❌'}")
    print(f"  AutoStrategy:           {'✅' if success_auto else '❌'}")
    print(f"  Pydantic直传:           {'✅' if success_none else '❌'}")
    print(f"  json_object (无工具):   {'✅' if success_json else '❌'}")
    print(f"  json_object (+工具):    {'✅' if success_json_tool else '❌'}")
    print(f"  with_structured_output: {'✅' if success_with else '❌'}")
    print(f"  prompt内嵌schema+工具: {'✅' if success_prompt_schema else '❌'}")
    print()
    print("【非thinking 模式（显式 disabled）】")
    print(f"  普通工具:               {'✅' if success_no_think_normal else '❌'}")
    print(f"  ToolStrategy:           {'✅' if success_no_think_tool else '❌'}")
    print(f"  ProviderStrategy:       {'✅' if success_no_think_provider else '❌'}")
    print(f"  AutoStrategy:           {'✅' if success_no_think_auto else '❌'}")
    print(f"  Pydantic直传:           {'✅' if success_no_think_pydantic else '❌'}")
    print("=" * 60)
