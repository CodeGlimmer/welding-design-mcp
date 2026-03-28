from enum import Enum
from typing import Union

from welding_app.welding_scenario.solder_joint import SolderJoint
from welding_app.welding_scenario.weld_seam import WeldSeam


class Action(Enum):
    ADD_SOLDER_JOINT = 0
    ADD_WELDING_SEAM = 1


class Command:
    def __init__(
        self,
        action: Action,
        action_item: Union[SolderJoint, WeldSeam, list[SolderJoint], None] = None,
    ):
        self._action = action
        self._action_item = action_item

    def undo(self):
        match self._action:
            case Action.ADD_SOLDER_JOINT:
                if isinstance(self._action_item, list):
                    return ("delete_batch", self._action_item)
                return ("delete", self._action_item)
            case Action.ADD_WELDING_SEAM:
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
        if not self._commands:
            return

        command = self._commands.pop()
        undo_result = command.undo()
        match undo_result:
            case ("delete", item):
                try:
                    self._obj.remove(item)
                except KeyError:
                    if hasattr(item, "_id") and item._id:
                        for obj in list(self._obj):
                            if hasattr(obj, "_id") and obj._id == item._id:
                                self._obj.remove(obj)
                                break
            case ("delete_batch", items):
                for item in items:
                    try:
                        self._obj.remove(item)
                    except KeyError:
                        if hasattr(item, "_id") and item._id:
                            for obj in list(self._obj):
                                if hasattr(obj, "_id") and obj._id == item._id:
                                    self._obj.remove(obj)
                                    break
            case _:
                pass
