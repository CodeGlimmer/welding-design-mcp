import json
import re
import struct
import zipfile
from pathlib import Path


def hex_to_float64(hex_str):
    try:
        clean_hex = hex_str.strip()
        if not clean_hex:
            return 0.0
        return struct.unpack(">d", bytes.fromhex(clean_hex))[0]
    except Exception:
        return 0.0


def extract_clean_welding_points(s):
    # 匹配模式不变
    block_pattern = re.compile(
        r'm_bsName:"(?P<name>[^"]+)",.*?m_spLocPosture:"(?P<posture>[^"]+)"', re.DOTALL
    )

    # 定义需要排除的非路径点关键词
    blacklist = {
        "PathHistory",
        "PFM",
        "通用",
        "RelativePosition",
        "Compensation",
        "Instruction",
    }

    results = []
    for match in block_pattern.finditer(s):
        name = match.group("name")

        # 过滤黑名单关键词
        if any(word in name for word in blacklist):
            continue

        posture_str = match.group("posture")
        parts = posture_str.split()

        if len(parts) >= 15:
            x = hex_to_float64(parts[12])
            y = hex_to_float64(parts[13])
            z = hex_to_float64(parts[14])

            # 过滤掉全 0 的逻辑节点
            if x == 0.0 and y == 0.0 and z == 0.0:
                continue

            results.append(
                {"name": name, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}
            )

    return results


def extract_path_json(robx_path: str) -> str:
    """
    从 robx 文件中提取 data/Path.json 的内容。

    Args:
        robx_path: .robx 文件路径

    Returns:
        Path.json 的内容字符串，如果出错则返回空字符串
    """
    try:
        path = Path(robx_path)
        if not path.exists() or not path.is_file():
            return ""

        with zipfile.ZipFile(path, "r") as zf:
            if "data/Path.json" not in zf.namelist():
                return ""

            with zf.open("data/Path.json") as f:
                return str(extract_clean_welding_points(f.read().decode("utf-8")))

    except (zipfile.BadZipFile, OSError, IOError, KeyError):
        return ""
