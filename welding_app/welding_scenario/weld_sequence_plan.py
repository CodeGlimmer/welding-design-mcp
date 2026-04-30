from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from .solder_joint import SolderJointModel


class LinearWeldingTask(BaseModel):
    """线性化的最小焊接任务单元"""

    index: int = Field(..., description="任务在序列中的序号")
    task_type: Literal["solder_joint", "sub_seam"] = Field(
        ..., description="任务类型：焊点 或 子焊缝段"
    )
    solder_joint: Optional[SolderJointModel] = Field(
        default=None, description="焊点任务（task_type 为 solder_joint 时有效）"
    )
    sub_seam: Optional[tuple[SolderJointModel, SolderJointModel]] = Field(
        default=None,
        description="子焊缝段任务（task_type 为 sub_seam 时有效），(起点, 终点)",
    )
    seam_id: Optional[str] = Field(
        default=None,
        description="所属焊缝ID（仅 sub_seam 类型有效，用于拼接 param_entity_id）",
    )

    @property
    def param_entity_id(self) -> str:
        """获取用于绑定工艺参数的唯一ID"""
        if self.task_type == "solder_joint":
            if not self.solder_joint or not self.solder_joint.position.id:
                raise ValueError("焊点任务缺少 position.id")
            return self.solder_joint.position.id
        else:
            if not self.seam_id:
                raise ValueError("子焊缝任务缺少 seam_id")
            start_id = self.sub_seam[0].position.id if self.sub_seam else None
            if not start_id:
                raise ValueError("子焊缝段的起点缺少 position.id")
            end_id = self.sub_seam[1].position.id if self.sub_seam else None
            if not end_id:
                raise ValueError("子焊缝段的终点缺少 position.id")
            return f"{self.seam_id}-{start_id}-{end_id}"

    def __str__(self) -> str:
        if self.task_type == "solder_joint":
            sj = self.solder_joint
            if sj:
                name = sj.name or sj.position.id or f"#{self.index}"
            else:
                name = f"#{self.index}"
            return f"[{self.index}] 焊点: {name}"
        else:
            sub = self.sub_seam
            if sub:
                start_name = sub[0].name or sub[0].position.id or "?"
                end_name = sub[1].name or sub[1].position.id or "?"
            else:
                start_name, end_name = "?", "?"
            return f"[{self.index}] 焊缝段({self.seam_id}): {start_name} → {end_name}"


class WeldingSequenceNavigator:
    """焊接序列导航器 — 将复杂模型线性化并提供遍历能力"""

    def __init__(self, model: "WeldingSequenceSortModel"):
        self._tasks: List[LinearWeldingTask] = self._linearize(model)
        self._current_index: int = 0

    @classmethod
    def from_tasks(cls, tasks: List[LinearWeldingTask]) -> "WeldingSequenceNavigator":
        """从已排序的线性任务列表创建导航器。"""
        nav = cls.__new__(cls)
        nav._tasks = [task.model_copy() for task in tasks]
        nav._current_index = 0
        return nav

    def _linearize(self, model: "WeldingSequenceSortModel") -> List[LinearWeldingTask]:
        plan = model.sequence_plan
        tasks: List[LinearWeldingTask] = []

        if isinstance(plan, SolderJointsSortModel):
            for sj in plan.solder_joint_sort:
                tasks.append(
                    LinearWeldingTask(
                        index=0, task_type="solder_joint", solder_joint=sj
                    )
                )

        elif isinstance(plan, SolderJointMixedWeldSeamSortModel):
            # 焊点
            for sj in plan.solder_joints_sort.solder_joint_sort:
                tasks.append(
                    LinearWeldingTask(
                        index=0, task_type="solder_joint", solder_joint=sj
                    )
                )
            # 焊缝段
            for seam_model in plan.weld_seam_sort.welding_seam_sort:
                for sub_seam in seam_model.sub_seam_sort:
                    tasks.append(
                        LinearWeldingTask(
                            index=0,
                            task_type="sub_seam",
                            sub_seam=sub_seam,
                            seam_id=seam_model.seam_id,
                        )
                    )

        for i, task in enumerate(tasks):
            task.index = i

        return tasks

    # -- 导航方法 --

    def current(self) -> Optional[LinearWeldingTask]:
        if not self._tasks:
            return None
        return self._tasks[self._current_index]

    def next(self) -> Optional[LinearWeldingTask]:
        if self._current_index + 1 >= len(self._tasks):
            return None
        self._current_index += 1
        return self._tasks[self._current_index]

    def prev(self) -> Optional[LinearWeldingTask]:
        if self._current_index - 1 < 0:
            return None
        self._current_index -= 1
        return self._tasks[self._current_index]

    def goto(self, index: int) -> Optional[LinearWeldingTask]:
        if index < 0 or index >= len(self._tasks):
            return None
        self._current_index = index
        return self._tasks[self._current_index]

    def reset(self):
        self._current_index = 0

    def is_end(self) -> bool:
        return self._current_index >= len(self._tasks) - 1

    def is_empty(self) -> bool:
        return len(self._tasks) == 0

    def total_count(self) -> int:
        return len(self._tasks)

    def display_current(self) -> str:
        task = self.current()
        if task is None:
            return "无任务"
        return str(task)

    @property
    def all_tasks(self) -> List[LinearWeldingTask]:
        return list(self._tasks)


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
    seam_id: str = Field(..., description="所属焊缝的ID")
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


if __name__ == "__main__":
    print(WeldingSequenceSortModel.model_json_schema())
