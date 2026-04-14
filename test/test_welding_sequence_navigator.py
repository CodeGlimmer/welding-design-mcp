import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from welding_app.welding_scenario.solder_joint import (
    GeometryPointModel,
    SolderJointModel,
)
from welding_app.welding_scenario.weld_sequence_plan import (
    LinearWeldingTask,
    SolderJointMixedWeldSeamSortModel,
    SolderJointsSortModel,
    WeldingSequenceNavigator,
    WeldingSequenceSortModel,
    WeldSeamSortModel,
    WeldSeamsSortModel,
)


class TestLinearWeldingTask(unittest.TestCase):
    def _make_solder_joint(self, joint_id: str, name: str | None = None):
        return SolderJointModel(
            position=GeometryPointModel(x=0.0, y=0.0, z=0.0, id=joint_id),
            name=name,
        )

    def test_param_entity_id_solder_joint(self):
        sj = self._make_solder_joint("jp1", "焊点1")
        task = LinearWeldingTask(index=0, task_type="solder_joint", solder_joint=sj)
        self.assertEqual(task.param_entity_id, "jp1")

    def test_param_entity_id_sub_seam(self):
        start = self._make_solder_joint("jp_start")
        end = self._make_solder_joint("jp_end")
        task = LinearWeldingTask(
            index=0, task_type="sub_seam", sub_seam=(start, end), seam_id="seam1"
        )
        self.assertEqual(task.param_entity_id, "seam1-jp_start")

    def test_param_entity_id_missing_solder_joint_id_raises(self):
        sj = self._make_solder_joint(None)
        task = LinearWeldingTask(index=0, task_type="solder_joint", solder_joint=sj)
        with self.assertRaises(ValueError):
            _ = task.param_entity_id

    def test_param_entity_id_missing_seam_id_raises(self):
        start = self._make_solder_joint("jp_start")
        end = self._make_solder_joint("jp_end")
        task = LinearWeldingTask(index=0, task_type="sub_seam", sub_seam=(start, end))
        with self.assertRaises(ValueError):
            _ = task.param_entity_id

    def test_str_solder_joint(self):
        sj = self._make_solder_joint("jp1", "焊点1")
        task = LinearWeldingTask(index=0, task_type="solder_joint", solder_joint=sj)
        self.assertIn("焊点", str(task))
        self.assertIn("焊点1", str(task))

    def test_str_sub_seam(self):
        start = self._make_solder_joint("jp1", "起点")
        end = self._make_solder_joint("jp2", "终点")
        task = LinearWeldingTask(
            index=1, task_type="sub_seam", sub_seam=(start, end), seam_id="seam1"
        )
        self.assertIn("seam1", str(task))
        self.assertIn("起点", str(task))
        self.assertIn("终点", str(task))


class TestWeldingSequenceNavigator(unittest.TestCase):
    def _make_solder_joint(self, joint_id: str, name: str | None = None):
        return SolderJointModel(
            position=GeometryPointModel(x=0.0, y=0.0, z=0.0, id=joint_id),
            name=name,
        )

    def _make_pure_solder_joints_model(self):
        sj1 = self._make_solder_joint("jp1", "焊点1")
        sj2 = self._make_solder_joint("jp2", "焊点2")
        sj3 = self._make_solder_joint("jp3", "焊点3")
        return SolderJointsSortModel(
            solder_joint_sort=[sj1, sj2, sj3],
            best_fitness=0.5,
            best_fitness_history=[0.8, 0.6, 0.5],
        )

    def _make_mixed_model(self):
        # 焊点
        sj1 = self._make_solder_joint("jp1", "焊点1")
        sj2 = self._make_solder_joint("jp2", "焊点2")
        solder_joints_sort = SolderJointsSortModel(
            solder_joint_sort=[sj1, sj2],
            best_fitness=0.3,
            best_fitness_history=[0.5, 0.3],
        )

        # 焊缝段
        start1 = self._make_solder_joint("jp_start1")
        end1 = self._make_solder_joint("jp_end1")
        start2 = self._make_solder_joint("jp_end1")
        end2 = self._make_solder_joint("jp_end2")

        seam1 = WeldSeamSortModel(
            seam_id="seam1",
            sub_seam_sort=[(start1, end1), (end1, end2)],
        )
        seam2 = WeldSeamSortModel(
            seam_id="seam2",
            sub_seam_sort=[(start2, end2)],
        )
        weld_seam_sort = WeldSeamsSortModel(welding_seam_sort=[seam1, seam2])

        return SolderJointMixedWeldSeamSortModel(
            solder_joints_sort=solder_joints_sort,
            weld_seam_sort=weld_seam_sort,
        )

    def test_linearize_pure_solder_joints(self):
        plan = self._make_pure_solder_joints_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        self.assertEqual(nav.total_count(), 3)
        self.assertFalse(nav.is_end())

        task = nav.current()
        self.assertEqual(task.index, 0)
        self.assertEqual(task.task_type, "solder_joint")
        self.assertEqual(task.param_entity_id, "jp1")

        task = nav.next()
        self.assertEqual(task.index, 1)
        self.assertEqual(task.param_entity_id, "jp2")

        task = nav.next()
        self.assertEqual(task.index, 2)
        self.assertTrue(nav.is_end())

        # 再 next 应返回 None
        self.assertIsNone(nav.next())

    def test_linearize_mixed_model(self):
        plan = self._make_mixed_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        # 2 个焊点 + 3 个子焊缝段 = 5
        self.assertEqual(nav.total_count(), 5)

        # 前两个是焊点
        self.assertEqual(nav.current().task_type, "solder_joint")
        self.assertEqual(nav.next().task_type, "solder_joint")

        # 后面三个是子焊缝
        for _ in range(3):
            task = nav.next()
            self.assertEqual(task.task_type, "sub_seam")
            self.assertIn("seam", task.param_entity_id)

        self.assertIsNone(nav.next())

    def test_prev_navigation(self):
        plan = self._make_pure_solder_joints_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        nav.next()
        nav.next()
        self.assertEqual(nav.current().index, 2)

        task = nav.prev()
        self.assertEqual(task.index, 1)

        nav.prev()
        self.assertIsNone(nav.prev())  # 已在最前

    def test_goto_and_reset(self):
        plan = self._make_pure_solder_joints_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        task = nav.goto(2)
        self.assertEqual(task.index, 2)

        self.assertIsNone(nav.goto(10))  # 越界

        nav.reset()
        self.assertEqual(nav.current().index, 0)

    def test_empty_model(self):
        plan = SolderJointsSortModel(
            solder_joint_sort=[],
            best_fitness=0.0,
            best_fitness_history=[],
        )
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        self.assertTrue(nav.is_empty())
        self.assertEqual(nav.total_count(), 0)
        self.assertIsNone(nav.current())
        self.assertEqual(nav.display_current(), "无任务")

    def test_display_current(self):
        plan = self._make_pure_solder_joints_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        display = nav.display_current()
        self.assertIn("0", display)
        self.assertIn("焊点", display)

    def test_all_tasks(self):
        plan = self._make_mixed_model()
        model = WeldingSequenceSortModel(sequence_plan=plan)
        nav = WeldingSequenceNavigator(model)

        tasks = nav.all_tasks
        self.assertEqual(len(tasks), 5)
        # 确保是独立副本（列表拷贝）
        tasks.clear()
        self.assertEqual(nav.total_count(), 5)


if __name__ == "__main__":
    unittest.main()
