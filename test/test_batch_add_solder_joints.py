import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from welding_app.agents.sub_agents.welding_scenario_parsing_agent.command import (
    Action,
    Command,
    Commands,
)
from welding_app.welding_scenario.solder_joint import (
    GeometryPointModel,
    SolderJoint,
    SolderJointModel,
)


class TestBatchAddSolderJoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_command_with_batch_items(self):
        """测试 Command 类能处理批量焊点"""
        point1 = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="p1")
        point2 = GeometryPointModel(x=1.0, y=1.0, z=1.0, id="p2")

        joint1 = SolderJointModel(position=point1, name="焊点1").to_SolderJoint()
        joint2 = SolderJointModel(position=point2, name="焊点2").to_SolderJoint()

        command = Command(
            action=Action.ADD_SOLDER_JOINT,
            action_item=[joint1, joint2],
        )

        result = command.undo()
        self.assertEqual(result[0], "delete_batch")
        self.assertEqual(len(result[1]), 2)  # type: ignore

    def test_commands_undo_batch(self):
        """测试 Commands 类能批量撤回"""
        scenario: set = set()
        commands_history = Commands(scenario)

        point1 = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="p1")
        point2 = GeometryPointModel(x=1.0, y=1.0, z=1.0, id="p2")

        joint1 = SolderJointModel(position=point1, name="焊点1").to_SolderJoint()
        joint2 = SolderJointModel(position=point2, name="焊点2").to_SolderJoint()

        commands_history.add_command(
            Command(
                action=Action.ADD_SOLDER_JOINT,
                action_item=[joint1, joint2],
            )
        )

        scenario.add(joint1)
        scenario.add(joint2)

        self.assertEqual(len(scenario), 2)

        commands_history.undo()

        self.assertEqual(len(scenario), 0)

    def test_single_solder_joint_still_works(self):
        """测试单个焊点的添加和撤回仍然正常"""
        scenario: set = set()
        commands_history = Commands(scenario)

        point = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="p1")
        joint = SolderJointModel(position=point, name="焊点1").to_SolderJoint()

        commands_history.add_command(
            Command(
                action=Action.ADD_SOLDER_JOINT,
                action_item=joint,
            )
        )

        scenario.add(joint)
        self.assertEqual(len(scenario), 1)

        commands_history.undo()
        self.assertEqual(len(scenario), 0)


if __name__ == "__main__":
    unittest.main()
