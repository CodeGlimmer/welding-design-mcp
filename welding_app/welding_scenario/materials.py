from enum import Enum, unique


@unique
class WeldingMaterialBIW(Enum):
    """
    白车身焊接材料枚举类
    涵盖电极材料、被焊板材、辅助材料、弧焊/激光焊材料四大类
    """

    # -------------------------- 1. 电极材料（点焊核心） --------------------------
    ELECTRODE_CUCRZR = "CuCrZr"  # 铬锆铜电极（主流点焊电极）
    ELECTRODE_CUZIRCONIUM = "CuZr"  # 锆铜电极
    ELECTRODE_CUBERYLLIUM = "CuBe"  # 铍铜电极（高强度耐磨）
    ELECTRODE_CAP = "Electrode Cap"  # 电极帽（易损件）
    ELECTRODE_SHANK = "Electrode Shank"  # 电极杆
    ELECTRODE_ARM = "Electrode Arm"  # 电极臂

    # -------------------------- 2. 被焊板材（车身本体） --------------------------
    STEEL_DC04 = "DC04"  # 低碳冷轧钢
    STEEL_DC06 = "DC06"  # 低碳冷轧钢
    STEEL_DP600 = "DP600"  # 双相钢（高强度）
    STEEL_DP800 = "DP800"  # 双相钢（高强度）
    STEEL_HR340 = "HR340"  # 热轧高强钢
    STEEL_HR440 = "HR440"  # 热轧高强钢
    ALUMINUM_ALLOY = "Aluminum Alloy"  # 铝合金（轻量化）
    ZINC_COATED_STEEL = "Zinc-Coated Steel"  # 镀锌钢板
    HOT_STAMPED_STEEL = "Hot-Stamped Steel"  # 热成型钢

    # -------------------------- 3. 辅助材料 --------------------------
    WELDING_LUBRICANT = "Welding Lubricant"  # 电极润滑/防粘剂
    CLEANING_FLUID = "Cleaning Fluid"  # 电极清洗液
    ANTI_BONDING_AGENT = "Anti-Bonding Agent"  # 防粘剂

    # -------------------------- 4. 弧焊/激光焊材料 --------------------------
    SOLID_WIRE = "Solid Wire"  # 实芯焊丝
    FLUX_CORED_WIRE = "Flux-Cored Wire"  # 药芯焊丝
    SHIELDING_GAS = "Shielding Gas"  # 保护气体（Ar/CO₂）

    def get_chinese_name(self) -> str:
        """
        扩展方法：获取焊接材料的中文名称（便于界面展示/日志输出）
        """
        name_mapping = {
            self.ELECTRODE_CUCRZR: "铬锆铜电极",
            self.ELECTRODE_CUZIRCONIUM: "锆铜电极",
            self.ELECTRODE_CUBERYLLIUM: "铍铜电极",
            self.ELECTRODE_CAP: "电极帽",
            self.ELECTRODE_SHANK: "电极杆",
            self.ELECTRODE_ARM: "电极臂",
            self.STEEL_DC04: "DC04低碳冷轧钢",
            self.STEEL_DC06: "DC06低碳冷轧钢",
            self.STEEL_DP600: "DP600双相钢",
            self.STEEL_DP800: "DP800双相钢",
            self.STEEL_HR340: "HR340热轧高强钢",
            self.STEEL_HR440: "HR440热轧高强钢",
            self.ALUMINUM_ALLOY: "铝合金",
            self.ZINC_COATED_STEEL: "镀锌钢板",
            self.HOT_STAMPED_STEEL: "热成型钢",
            self.WELDING_LUBRICANT: "电极润滑/防粘剂",
            self.CLEANING_FLUID: "电极清洗液",
            self.ANTI_BONDING_AGENT: "防粘剂",
            self.SOLID_WIRE: "实芯焊丝",
            self.FLUX_CORED_WIRE: "药芯焊丝",
            self.SHIELDING_GAS: "保护气体",
        }
        return name_mapping.get(self, "未知焊接材料")
