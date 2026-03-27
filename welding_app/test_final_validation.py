#!/usr/bin/env python3
"""
最终验证测试 - 验证所有工具函数都可用
"""

import json
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from welding_app.agents.sub_agents.welding_scenario_parsing_agent.parsing_agent_tools import (
    generate_scenario_builder_toolkit,
)
from welding_app.welding_scenario.materials import WeldingMaterialBIW
from welding_app.welding_scenario.solder_joint import (
    GeometryPointModel,
    SolderJointModel,
)
from welding_app.welding_scenario.weld_seam import GeometryStraightLineModel


def test_all_tools():
    """测试所有工具函数"""
    print("=" * 60)
    print("最终验证测试 - 验证所有工具函数都可用")
    print("=" * 60)

    # 生成工具包
    print("\n1. 生成场景构建工具包...")
    toolkit = generate_scenario_builder_toolkit()

    # 验证工具数量
    assert len(toolkit) == 5, f"工具包应该包含5个工具，实际包含{len(toolkit)}个"
    print(f"   ✅ 工具包包含{len(toolkit)}个工具")

    # 获取工具函数
    clear_scenario = toolkit[0]
    add_solder_joint = toolkit[1]
    add_weld_seam = toolkit[2]
    undo = toolkit[3]
    show_scenario = toolkit[4]

    print("   工具列表:")
    print("     1. clear_scenario - 清空场景")
    print("     2. add_solder_joint - 添加焊点")
    print("     3. add_weld_seam - 添加焊缝")
    print("     4. undo - 撤回操作")
    print("     5. show_scenario - 显示场景")

    # 测试1: 清空场景
    print("\n2. 测试clear_scenario...")
    result = clear_scenario.invoke({})
    assert result == "场景已清空", (
        f"clear_scenario应该返回'场景已清空'，实际返回: {result}"
    )
    print(f"   ✅ clear_scenario工作正常: {result}")

    # 测试2: 添加焊点
    print("\n3. 测试add_solder_joint...")
    position = GeometryPointModel(x=10.0, y=20.0, z=30.0, id="test_point_1")
    result = add_solder_joint.invoke(
        {
            "position": position,
            "name": "测试焊点",
            "base_material": [WeldingMaterialBIW.STEEL_DC04.value],
            "surface_normal": (0.0, 0.0, 1.0),
            "connected_parts": ["部件A", "部件B"],
            "thicknss_combination": [1.5, 2.0],
        }
    )
    assert result == "焊点已添加", (
        f"add_solder_joint应该返回'焊点已添加'，实际返回: {result}"
    )
    print(f"   ✅ add_solder_joint工作正常: {result}")

    # 测试3: 显示场景
    print("\n4. 测试show_scenario...")
    scenario_info = show_scenario.invoke({})

    # 验证场景信息结构
    required_keys = ["total_items", "solder_joints", "weld_seams"]
    for key in required_keys:
        assert key in scenario_info, f"场景信息缺少键: {key}"

    assert scenario_info["total_items"] == 1, (
        f"应该有1个焊点，实际有{scenario_info['total_items']}个"
    )
    assert len(scenario_info["solder_joints"]) == 1, (
        f"应该有1个焊点，实际有{len(scenario_info['solder_joints'])}个"
    )
    assert len(scenario_info["weld_seams"]) == 0, (
        f"应该没有焊缝，实际有{len(scenario_info['weld_seams'])}个"
    )

    # 验证焊点信息完整性
    joint = scenario_info["solder_joints"][0]
    joint_required_keys = [
        "id",
        "position",
        "name",
        "base_material",
        "surface_normal",
        "connected_parts",
        "thicknss_combination",
        "full_model",
    ]
    for key in joint_required_keys:
        assert key in joint, f"焊点信息缺少键: {key}"

    # 验证JSON可序列化
    try:
        json.dumps(scenario_info)
        print("   ✅ show_scenario返回的数据可JSON序列化")
    except Exception as e:
        raise AssertionError(f"show_scenario返回的数据不可JSON序列化: {e}")

    print(f"   ✅ show_scenario工作正常")
    print(f"     总项目数: {scenario_info['total_items']}")
    print(f"     焊点数量: {len(scenario_info['solder_joints'])}")
    print(f"     焊缝数量: {len(scenario_info['weld_seams'])}")

    # 测试4: 添加焊缝
    print("\n5. 测试add_weld_seam...")

    # 创建几何直线
    start_point = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="line_start")
    end_point = GeometryPointModel(x=100.0, y=100.0, z=0.0, id="line_end")
    line = GeometryStraightLineModel(
        start_point=start_point, end_point=end_point, id="test_line"
    )

    # 创建焊缝上的焊点列表
    solder_joints = [
        SolderJointModel(
            position=GeometryPointModel(x=10.0, y=10.0, z=0.0, id="seam_point_1"),
            base_material=[WeldingMaterialBIW.STEEL_DC04],
            name="焊缝焊点1",
        ),
        SolderJointModel(
            position=GeometryPointModel(x=50.0, y=50.0, z=0.0, id="seam_point_2"),
            base_material=[WeldingMaterialBIW.STEEL_DP600],
            name="焊缝焊点2",
        ),
    ]

    result = add_weld_seam.invoke(
        {
            "line": line,
            "solder_joints": solder_joints,
            "id": "test_seam",
            "name": "测试焊缝",
        }
    )

    assert result == "焊缝已添加", (
        f"add_weld_seam应该返回'焊缝已添加'，实际返回: {result}"
    )
    print(f"   ✅ add_weld_seam工作正常: {result}")

    # 验证场景更新
    scenario_info = show_scenario.invoke({})
    assert scenario_info["total_items"] == 2, (
        f"应该有2个项目（1焊点+1焊缝），实际有{scenario_info['total_items']}个"
    )
    assert len(scenario_info["weld_seams"]) == 1, (
        f"应该有1个焊缝，实际有{len(scenario_info['weld_seams'])}个"
    )
    print(f"   ✅ 场景更新正确")
    print(f"     总项目数: {scenario_info['total_items']}")
    print(f"     焊点数量: {len(scenario_info['solder_joints'])}")
    print(f"     焊缝数量: {len(scenario_info['weld_seams'])}")

    # 测试5: 撤回操作
    print("\n6. 测试undo...")

    # 撤回焊缝
    result = undo.invoke({})
    assert result == "已撤回上一步操作", (
        f"undo应该返回'已撤回上一步操作'，实际返回: {result}"
    )
    print(f"   ✅ undo工作正常: {result}")

    # 验证撤回效果
    scenario_info = show_scenario.invoke({})
    assert scenario_info["total_items"] == 1, (
        f"撤回后应该有1个焊点，实际有{scenario_info['total_items']}个"
    )
    assert len(scenario_info["weld_seams"]) == 0, (
        f"撤回后应该没有焊缝，实际有{len(scenario_info['weld_seams'])}个"
    )
    print(f"   ✅ 撤回效果正确")
    print(f"     总项目数: {scenario_info['total_items']}")
    print(f"     焊点数量: {len(scenario_info['solder_joints'])}")
    print(f"     焊缝数量: {len(scenario_info['weld_seams'])}")

    # 撤回焊点
    result = undo.invoke({})
    assert result == "已撤回上一步操作", (
        f"undo应该返回'已撤回上一步操作'，实际返回: {result}"
    )

    # 验证场景为空
    scenario_info = show_scenario.invoke({})
    assert scenario_info["total_items"] == 0, (
        f"撤回所有操作后应该没有项目，实际有{scenario_info['total_items']}个"
    )
    print(f"   ✅ 所有操作都已撤回，场景为空")

    # 测试没有可撤回操作的情况
    result = undo.invoke({})
    assert result == "没有可撤回的操作", (
        f"没有可撤回操作时应该返回'没有可撤回的操作'，实际返回: {result}"
    )
    print(f"   ✅ 没有可撤回操作时处理正确: {result}")

    # 测试6: 完整工作流程
    print("\n7. 测试完整工作流程...")

    # 清空场景
    clear_scenario.invoke({})

    # 添加多个焊点
    for i in range(3):
        position = GeometryPointModel(
            x=i * 20.0, y=i * 30.0, z=i * 40.0, id=f"workflow_point_{i}"
        )
        add_solder_joint.invoke(
            {
                "position": position,
                "name": f"工作流焊点{i}",
                "base_material": [WeldingMaterialBIW.STEEL_DC04.value],
            }
        )

    # 添加焊缝
    line = GeometryStraightLineModel(
        start_point=GeometryPointModel(x=0.0, y=0.0, z=0.0, id="wf_line_start"),
        end_point=GeometryPointModel(x=200.0, y=200.0, z=0.0, id="wf_line_end"),
        id="workflow_line",
    )

    seam_solder_joints = [
        SolderJointModel(
            position=GeometryPointModel(x=50.0, y=50.0, z=0.0, id="wf_seam_point_1"),
            base_material=[WeldingMaterialBIW.STEEL_DP800],
            name="工作流焊缝焊点1",
        ),
        SolderJointModel(
            position=GeometryPointModel(x=150.0, y=150.0, z=0.0, id="wf_seam_point_2"),
            base_material=[WeldingMaterialBIW.ZINC_COATED_STEEL],
            name="工作流焊缝焊点2",
        ),
    ]

    add_weld_seam.invoke(
        {
            "line": line,
            "solder_joints": seam_solder_joints,
            "id": "workflow_seam",
            "name": "工作流焊缝",
        }
    )

    # 显示最终场景
    final_scenario = show_scenario.invoke({})

    print(f"   ✅ 完整工作流程测试通过")
    print(f"     最终场景统计:")
    print(f"       总项目数: {final_scenario['total_items']}")
    print(f"       独立焊点: {len(final_scenario['solder_joints'])}")
    print(f"       焊缝数量: {len(final_scenario['weld_seams'])}")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！所有工具函数都可用且工作正常。")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        test_all_tools()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试发生异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
