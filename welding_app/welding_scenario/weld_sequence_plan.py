from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .solder_joint import SolderJointModel


class SolderJointsSortModel(BaseModel):
    """焊点集合排列顺序"""

    type_flag: Literal["SolderJointsSortModel"] = "SolderJointsSortModel"
    solder_joint_sort: Annotated[
        list[SolderJointModel], Field(description="最佳的焊点焊接顺序排列")
    ]
    best_fitness: Annotated[
        float,
        Field(
            description="最佳的种群适应度，由于采用了遗传算法来求解最佳焊接顺序，所以有此项。这一项的具体意义是焊点集合的热集中度，越低越好"
        ),
    ]
    best_fitness_history: Annotated[
        list[float],
        Field(
            description="记录焊点集合焊接顺序历史上的最佳适应度，可以用于后期的视图展示"
        ),
    ]


class WeldSeamSortModel(BaseModel):
    sub_seam_sort: Annotated[
        list[tuple[SolderJointModel, SolderJointModel]],
        Field(
            description="一个焊缝由焊接固定点被拆分成多个子焊缝，这里是子焊缝的焊接顺序，元素的第一项表示起始焊点，第二项是终点"
        ),
    ]


class WeldSeamsSortModel(BaseModel):
    welding_seam_sort: Annotated[
        list[WeldSeamSortModel], Field(description="多个焊缝，对焊缝的焊接顺序进行排序")
    ]


class SolderJointMixedWeldSeamSortModel(BaseModel):
    """焊点集合混合焊缝的方案"""

    type_flag: Literal["SolderJointMixedWeldSeamSortModel"] = (
        "SolderJointMixedWeldSeamSortModel"
    )
    solder_joints_sort: Annotated[
        SolderJointsSortModel, Field(description="焊点焊接顺序")
    ]
    weld_seam_sort: Annotated[WeldSeamsSortModel, Field(description="焊缝焊接顺序")]


class WeldingSequenceSortModel(BaseModel):
    sequence_plan: Union[SolderJointsSortModel, SolderJointMixedWeldSeamSortModel] = (
        Field(
            discriminator="type_flag",
            description="焊接方案序列顺序由两种类型，通过type_flag区分",
        )
    )
