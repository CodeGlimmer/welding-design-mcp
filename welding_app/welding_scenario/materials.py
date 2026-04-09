from enum import Enum, unique


@unique
class WeldingMaterialBIW(Enum):
    """
    白车身焊接材料枚举类
    """

    ELECTRODE_CUCRZR = "CuCrZr"
    ELECTRODE_CUZIRCONIUM = "CuZr"
    ELECTRODE_CUBERYLLIUM = "CuBe"
    ELECTRODE_CAP = "Electrode Cap"
    ELECTRODE_SHANK = "Electrode Shank"
    ELECTRODE_ARM = "Electrode Arm"

    STEEL_DC04 = "DC04"
    STEEL_DC06 = "DC06"
    STEEL_DP600 = "DP600"
    STEEL_DP800 = "DP800"
    STEEL_HR340 = "HR340"
    STEEL_HR440 = "HR440"
    ALUMINUM_ALLOY = "Aluminum Alloy"
    ZINC_COATED_STEEL = "Zinc-Coated Steel"
    HOT_STAMPED_STEEL = "Hot-Stamped Steel"

    WELDING_LUBRICANT = "Welding Lubricant"
    CLEANING_FLUID = "Cleaning Fluid"
    ANTI_BONDING_AGENT = "Anti-Bonding Agent"

    SOLID_WIRE = "Solid Wire"
    FLUX_CORED_WIRE = "Flux-Cored Wire"
    SHIELDING_GAS = "Shielding Gas"

    def get_chinese_name(self) -> str:
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


@unique
class WeldingProcessType(Enum):
    """焊接工艺类型"""

    SPOT_WELDING = "Spot Welding"  # 电阻点焊
    ARC_WELDING = "Arc Welding"  # 弧焊
    LASER_WELDING = "Laser Welding"  # 激光焊
    BONDING = "Bonding"  # 涂胶
