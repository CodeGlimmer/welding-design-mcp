import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastmcp import FastMCP
from pydantic import Field

from welding_app.server_types.file_transfer_types import (
    FileInfo,
    FilesInfo,
    UploadWeldingScenarioResult,
)


def register_file_transfer_tools(mcp: FastMCP):
    """注册文件上传下载工具"""

    @mcp.tool(
        description=f"""使用该工具上传焊接场景文件
        Returns:
            UploadWeldingScenarioResult: <json-schema>{UploadWeldingScenarioResult.model_json_schema()}</json-schema>
        """
    )
    def upload_welding_scenario(
        file_local_location: Annotated[
            str,
            Field(
                description="""文件的本地路径
            <usage>通过提供文件的本地路径，智能焊接系统将读取文件内容，解析焊接场景</usage>
            <constraints>系统目前只接受后缀名为json、txt、robx的文件。
            如果你没获取到满足这些条件的文件，你应该向用户报告不支持此类文件的解析</constraints>
            <backgrond>三维焊接场景的描述是复杂的，用户可能提供的文件内容可能包含三维模型、焊接参数、材料信息等多种信息。
            为了简化解析操作，这里的json用于结构化表示一个焊接场景。txt是描述型文件，用户提供尽可能丰富的文本信息用于描述场景。
            robx是收到支持的三维场景文件，如果用户上传该文件，系统则有可能提供更丰富的服务，比如运行仿真动画、提供性能报告等。</background>
            """
            ),
        ],
        file_description: Annotated[
            str,
            Field(
                description="""一个你自定义的字段，方便你检索检索文件时能够快速定位"""
            ),
        ],
    ) -> UploadWeldingScenarioResult:
        """上传焊接场景"""
        # 检查path是否存在
        file_path = Path(file_local_location).resolve()
        if not file_path.exists():
            return UploadWeldingScenarioResult(result=False)

        # 存储路径进入数据库
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent / "databases" / "welding_scenario.db"
        )
        welding_scenario_id = uuid.uuid4().hex
        try:
            with connect:
                cursor = connect.cursor()
                cursor.execute(
                    "insert into local_file (welding_scenario_id, file_position, file_description) values (?, ?, ?)",
                    (welding_scenario_id, file_local_location, file_description),
                )
        finally:
            connect.close()
        return UploadWeldingScenarioResult(id=welding_scenario_id, result=True)

    @mcp.tool(
        description=f"""返回单一文件或全部文件的信息
        Returns:
            FilesInfo: <json-schema>{FilesInfo.model_json_schema()}</json-schema>
        """
    )
    def get_uploaded_file_info(
        id: Annotated[
            Optional[str],
            Field(
                description="""获取你上传过的文件的信息
        有两种使用方式
        <usage1>传入空id，系统将返回所有库中的场景文件信息<warn>有些内容可能不是你本次会话上传的</warn></usage1>
        <usage2>传入具体id, 系统会返回这一项Id的内容</usage2>
        """
            ),
        ] = None,
    ):
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent / "databases" / "welding_scenario.db"
        )
        infos = None
        try:
            with connect:
                cursor = connect.cursor()
                if not id:
                    res = cursor.execute("select * from local_file;")
                    files_info = []
                    for file_info in res:
                        files_info.append(
                            FileInfo(
                                welding_scenario_id=file_info[1],
                                file_position=file_info[2],
                                file_description=file_info[3],
                            )
                        )
                    infos = FilesInfo(
                        is_single_file=False, files_info=files_info, file_info=None
                    )
                else:
                    res = cursor.execute(
                        "select * from local_file where welding_scenario_id = ?", (id,)
                    )
                    res = res.fetchone()
                    infos = FilesInfo(
                        is_single_file=True,
                        files_info=None,
                        file_info=FileInfo(
                            welding_scenario_id=res[1],
                            file_position=res[2],
                            file_description=res[3],
                        ),
                    )
        finally:
            connect.close()
        return infos
