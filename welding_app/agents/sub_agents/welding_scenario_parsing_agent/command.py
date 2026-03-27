from enum import Enum

from welding_app.welding_scenario.solder_joint import SolderJoint
from welding_app.welding_scenario.weld_seam import WeldSeam


class Action(Enum):
    ADD_SOLDER_JOINT = 0
    ADD_WELDING_SEAM = 1


class Command:
    def __init__(
        self,
        action: Action,
        action_item: SolderJoint | WeldSeam | None = None,
    ):
        self._action = action
        self._action_item = action_item

    def undo(self):
        match self._action:
            case Action.ADD_SOLDER_JOINT | Action.ADD_WELDING_SEAM:
                # 从队列中删除，此处没有具体操作
                return ("delete", self._action_item)
            case _:
                return None


class Commands:
    def __init__(self, obj: set[SolderJoint | WeldSeam]):
        """
        命令队列，用于保存操作命令'

        Args:
            obj: 操作的对象，为焊接场景
        """
        self._commands = []
        self._obj = obj

    def add_command(self, command: Command):
        self._commands.append(command)

    def undo(self):
        command = self._commands.pop()
        # 获取处理结果
        undo_result = command.undo()
        match undo_result:
            case ("delete", item):
                # 尝试从集合中删除项目，如果不存在则忽略
                try:
                    self._obj.remove(item)
                except KeyError:
                    # 项目可能已经被删除或不存在于集合中
                    # 这可能是由于对象相等性比较问题导致的
                    # 我们尝试通过ID查找并删除
                    if hasattr(item, "_id") and item._id:
                        # 尝试通过ID查找并删除
                        for obj in list(self._obj):
                            if hasattr(obj, "_id") and obj._id == item._id:
                                self._obj.remove(obj)
                                break
            case _:
                pass
