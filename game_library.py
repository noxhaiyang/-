"""
游戏 → 本地底图文件名映射。将图片放入 assets/games/ 目录，文件名与下方值一致。

共 10 个槽位：前三个为示例名，其余为占位名，可自行改显示名与图片。
"""
from __future__ import annotations

from pathlib import Path

# 显示名 -> 文件名（顺序即页面从左到右、从上到下的排列顺序）
GAME_BACKGROUND_FILES: dict[str, str] = {
    "PUBGM": "PUBGM.png",
    "罗布乐思": "罗布乐思.png",
    "和平精英": "和平精英.png",
    "三角洲行动": "三角洲行动.png",
    "王者荣耀": "王者荣耀.png",
    "暗区突围": "暗区突围.png",
    "steam": "steam.png",
    "永恒之塔2": "永恒之塔2.png",
    "战争雷霆": "战争雷霆.png",
    "HOK": "HOK.jpg",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent


def games_dir() -> Path:
    return project_root() / "assets" / "games"


def list_games() -> list[str]:
    return list(GAME_BACKGROUND_FILES.keys())


def background_path_for_game(game_name: str) -> Path:
    name = (game_name or "").strip()
    if name not in GAME_BACKGROUND_FILES:
        raise ValueError(f"未知游戏：{name}，可选：{', '.join(GAME_BACKGROUND_FILES)}")
    configured = games_dir() / GAME_BACKGROUND_FILES[name]
    if configured.is_file():
        return configured

    # 兼容扩展名变化：若配置是 .png，但实际为 .jpg/.jpeg/.webp，也能自动匹配
    stem = configured.stem.lower()
    for p in games_dir().iterdir():
        if not p.is_file():
            continue
        if p.stem.lower() != stem:
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return p
    return configured
