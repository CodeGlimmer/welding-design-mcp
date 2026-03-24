from typing import Annotated, Optional

from pydantic import BaseModel, Field


class UploadWeldingScenarioResult(BaseModel):
    id: Annotated[
        Optional[str],
        Field(
            description="上传场景文件后，系统会发挥给你一个id，用于指向该场景, 如果文件不存在则为null",
            default=None,
        ),
    ] = None
    result: Annotated[
        bool,
        Field(description="上传成功结果为true，如果不存在则会返回false", default=True),
    ] = True


class FileInfo(BaseModel):
    """单一文件的文件信息"""

    welding_scenario_id: Annotated[str, Field(description="场景的id")]
    file_position: Annotated[str, Field(description="文件在本机上存储的位置")]
    file_description: Annotated[str, Field(description="作为自定义字段，你传入的数据")]


class FilesInfo(BaseModel):
    """单一文件或多文件的信息"""

    is_single_file: Annotated[
        bool, Field(description="如果是单一文件，则为true，否则为false")
    ]
    files_info: Annotated[
        Optional[list[FileInfo]],
        Field(description="如果is_single_file为true此项为null，否则列出所有文件信息"),
    ]
    file_info: Annotated[
        Optional[FileInfo],
        Field(description="如果is_single_file为true，此项生效，否则为空"),
    ]


if __name__ == "__main__":
    print(FilesInfo.model_json_schema())
