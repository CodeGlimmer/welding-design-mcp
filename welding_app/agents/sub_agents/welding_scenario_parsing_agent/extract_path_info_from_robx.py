import zipfile
from pathlib import Path


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
                return f.read().decode("utf-8")

    except (zipfile.BadZipFile, OSError, IOError, KeyError):
        return ""
