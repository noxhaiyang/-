"""
竖版 9:16 视频封面生成：标题 + 游戏名；底图来自本地 assets/games/ 图库。
"""
from __future__ import annotations

import hashlib
import os
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from game_library import background_path_for_game, background_path_for_game_horizontal

# 9:16 竖版，常用短视频规格
WIDTH = 1080
HEIGHT = 1920

# 16:9 横版占位（后续可替换为真实生成管线）
HORIZONTAL_WIDTH = 1920
HORIZONTAL_HEIGHT = 1080


def _resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    img = img.convert("RGB")
    tw, th = target_w, target_h
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _font_candidates(bold: bool) -> list[str]:
    # Windows 常见中文字体
    windir = os.environ.get("WINDIR", r"C:\Windows")
    win_fonts = Path(windir) / "Fonts"
    windows = [
        str(win_fonts / "msyhbd.ttc"),
        str(win_fonts / "msyh.ttc"),
        str(win_fonts / "simhei.ttf"),
        str(win_fonts / "simsun.ttc"),
    ]
    # Linux / macOS 常见字体（Streamlit Cloud 多为 Linux）
    linux_macos = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]
    # Pillow 自带/可解析的回退字体（至少保证字号生效）
    pillow_fallback = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial.ttf",
    ]
    if bold:
        return windows + linux_macos + pillow_fallback
    return windows[1:] + linux_macos + pillow_fallback


def _download_noto_cjk_font(bold: bool) -> str | None:
    """
    云端无可用中文字体时，下载开源 Noto CJK 到本地缓存目录。
    仅作为最后兜底，下载失败则返回 None。
    """
    cache_dir = Path(__file__).resolve().parent / ".font_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = "NotoSansCJKsc-Bold.otf" if bold else "NotoSansCJKsc-Regular.otf"
    target = cache_dir / filename
    if target.is_file():
        return str(target)

    url = (
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/"
        + filename
    )
    try:
        urllib.request.urlretrieve(url, str(target))
    except Exception:
        return None
    return str(target) if target.is_file() else None


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_name in _font_candidates(bold):
        try:
            return ImageFont.truetype(font_name, size=size, index=0)
        except OSError:
            continue
    downloaded = _download_noto_cjk_font(bold)
    if downloaded:
        try:
            return ImageFont.truetype(downloaded, size=size, index=0)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap_lines(text: str, max_chars_per_line: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        wrapped = textwrap.wrap(paragraph, width=max_chars_per_line)
        lines.extend(wrapped if wrapped else [paragraph])
    return lines


def _title_two_lines(text: str) -> list[str]:
    """
    标题强制组织成两行，便于做短视频封面的大字风格。
    若用户本身输入了两行，则直接使用前两行。
    """
    raw = [p.strip() for p in text.split("\n") if p.strip()]
    if len(raw) >= 2:
        return [raw[0], raw[1]]
    if len(raw) == 1:
        s = raw[0]
    else:
        s = "未命名"
    if len(s) <= 10:
        return [s, ""]
    cut = len(s) // 2
    return [s[:cut].strip(), s[cut:].strip()]


def _draw_center_text_with_outline(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    center_x: int,
    top_y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    """黑色描边 + 主色填充。"""
    if not text:
        return
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = center_x - tw // 2

    # 黑描边（提升对比度）
    draw.text(
        (tx, top_y),
        text,
        font=font,
        fill=fill,
        stroke_width=10,
        stroke_fill=(0, 0, 0),
    )


def load_background_image(game_name: str, width: int, height: int) -> Image.Image:
    """从图库读取游戏对应底图并裁切为竖版 cover。"""
    path = background_path_for_game(game_name)
    if not path.is_file():
        raise FileNotFoundError(
            f"缺少底图文件：{path}\n请将对应图片放入 assets/games/ 目录（见 game_library.py 中的文件名）。"
        )
    img = Image.open(path).convert("RGB")
    return _resize_cover(img, width, height)


def load_background_image_horizontal(game_name: str, width: int, height: int) -> Image.Image:
    """从横图图库读取游戏对应底图并裁切为横版 cover。"""
    path = background_path_for_game_horizontal(game_name)
    if not path.is_file():
        raise FileNotFoundError(
            f"缺少横图底图文件：{path}\n请将对应图片放入 assets/games_horizontal/ 目录（见 game_library.py 中的文件名）。"
        )
    img = Image.open(path).convert("RGB")
    return _resize_cover(img, width, height)


def generate_cover(
    title: str,
    game_name: str,
    output_path: str | Path,
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
    accent: tuple[int, int, int] | None = None,
) -> Path:
    """生成竖版封面 PNG；底图为该游戏在 assets/games/ 下配置的本地图片。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = load_background_image(game_name, width, height)
    base = base.convert("RGBA")
    dim = Image.new("RGBA", (width, height), (0, 0, 0, 75))
    base = Image.alpha_composite(base, dim).convert("RGB")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    margin = int(width * 0.08)
    for i in range(margin):
        a = int(60 * (1 - i / margin))
        od.rectangle([i, i, width - 1 - i, height - 1 - i], outline=(0, 0, 0, a))
    base_rgba = base.convert("RGBA")
    base_rgba = Image.alpha_composite(base_rgba, overlay)
    base = base_rgba.convert("RGB")

    draw = ImageDraw.Draw(base)

    if accent is None:
        h = hashlib.sha256((game_name + title).encode()).digest()
        accent = (200 + h[0] % 55, 200 + h[1] % 55, 220 + h[2] % 35)

    # 不再限制两行：保留用户换行，并按宽度自动换行
    text = (title or "").strip() or "未命名"
    max_chars = max(8, width // 60)
    lines = _wrap_lines(text, max_chars_per_line=max_chars)
    if not lines:
        lines = ["未命名"]

    # 根据行数自动缩放字号，保证整体能放下
    target_top = int(height * 0.18)
    target_bottom = int(height * 0.62)
    max_block_h = max(240, target_bottom - target_top)

    font_size = 104
    line_spacing = 18
    while font_size >= 44:
        font = _load_font(font_size, bold=True)
        bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
        heights = [(b[3] - b[1]) for b in bboxes]
        block_h = sum(heights) + max(0, len(lines) - 1) * line_spacing
        max_w = max((b[2] - b[0]) for b in bboxes)
        if block_h <= max_block_h and max_w <= int(width * 0.88):
            break
        font_size -= 4
        line_spacing = max(10, line_spacing - 1)

    # 视觉上居中（在目标区域内）
    start_y = target_top + (max_block_h - block_h) // 2
    # 每行不同主色：以橙/绿/红为主，循环使用
    colors = [
        (255, 145, 35),  # 橙
        (55, 205, 105),  # 绿
        (255, 70, 70),   # 红
        (255, 215, 55),  # 黄
        (120, 210, 255), # 青蓝
        (190, 120, 255), # 紫
    ]
    y = start_y
    for idx, ln in enumerate(lines):
        _draw_center_text_with_outline(
            draw,
            ln,
            center_x=width // 2,
            top_y=y,
            font=font,
            fill=colors[idx % len(colors)],
        )
        y += heights[idx] + line_spacing

    base = base.convert("RGB")
    base = base.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))

    base.save(output_path, "PNG", optimize=True)
    return output_path.resolve()


def generate_cover_horizontal(
    title: str,
    game_name: str,
    output_path: str | Path,
    *,
    width: int = HORIZONTAL_WIDTH,
    height: int = HORIZONTAL_HEIGHT,
    accent: tuple[int, int, int] | None = None,
) -> Path:
    """生成横版封面 PNG；底图为该游戏在 assets/games_horizontal/ 下配置的本地图片。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = load_background_image_horizontal(game_name, width, height)
    base = base.convert("RGBA")
    dim = Image.new("RGBA", (width, height), (0, 0, 0, 65))
    base = Image.alpha_composite(base, dim).convert("RGB")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    margin = int(width * 0.04)
    for i in range(margin):
        a = int(52 * (1 - i / margin))
        od.rectangle([i, i, width - 1 - i, height - 1 - i], outline=(0, 0, 0, a))
    base_rgba = base.convert("RGBA")
    base_rgba = Image.alpha_composite(base_rgba, overlay)
    base = base_rgba.convert("RGB")

    draw = ImageDraw.Draw(base)

    if accent is None:
        h = hashlib.sha256((game_name + title).encode()).digest()
        accent = (200 + h[0] % 55, 200 + h[1] % 55, 220 + h[2] % 35)

    text = (title or "").strip() or "未命名"
    max_chars = max(10, width // 68)
    lines = _wrap_lines(text, max_chars_per_line=max_chars)
    if not lines:
        lines = ["未命名"]

    # 横版：把标题块放在偏下中部，留出上方画面主体
    target_top = int(height * 0.22)
    target_bottom = int(height * 0.88)
    max_block_h = max(180, target_bottom - target_top)

    font_size = 92
    line_spacing = 14
    while font_size >= 36:
        font = _load_font(font_size, bold=True)
        bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
        heights = [(b[3] - b[1]) for b in bboxes]
        block_h = sum(heights) + max(0, len(lines) - 1) * line_spacing
        max_w = max((b[2] - b[0]) for b in bboxes)
        if block_h <= max_block_h and max_w <= int(width * 0.9):
            break
        font_size -= 4
        line_spacing = max(10, line_spacing - 1)

    start_y = target_top + (max_block_h - block_h) // 2
    colors = [
        (255, 145, 35),  # 橙
        (55, 205, 105),  # 绿
        (255, 70, 70),  # 红
        (255, 215, 55),  # 黄
        (120, 210, 255),  # 青蓝
        (190, 120, 255),  # 紫
    ]
    y = start_y
    for idx, ln in enumerate(lines):
        _draw_center_text_with_outline(
            draw,
            ln,
            center_x=width // 2,
            top_y=y,
            font=font,
            fill=colors[idx % len(colors)],
        )
        y += heights[idx] + line_spacing

    base = base.convert("RGB")
    base = base.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))
    base.save(output_path, "PNG", optimize=True)
    return output_path.resolve()


def generate_placeholder_cover(
    text: str,
    output_path: str | Path,
    *,
    width: int,
    height: int,
    variant_label: str = "占位图",
) -> Path:
    """
    生成横版或竖版占位 PNG：灰底 + 文案 + 尺寸标注。
    后续可将此函数替换为真实生成逻辑，保持签名或封装一层即可。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = (text or "").strip() or "（无文案）"

    img = Image.new("RGB", (width, height), (42, 45, 52))
    draw = ImageDraw.Draw(img)
    # 细网格，便于看出是占位
    step = 48
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=(52, 55, 62), width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=(52, 55, 62), width=1)

    margin = max(24, int(min(width, height) * 0.06))
    max_chars = max(8, width // 42)
    lines = _wrap_lines(text, max_chars_per_line=max_chars)
    if len(lines) > 8:
        lines = lines[:7] + ["…"]

    title_font = _load_font(max(28, min(width, height) // 18), bold=True)
    sub_font = _load_font(max(20, min(width, height) // 28), bold=False)

    y = margin + int(height * 0.12)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        tx = (width - tw) // 2
        draw.text((tx, y), line, font=title_font, fill=(235, 238, 245))
        y += (bbox[3] - bbox[1]) + 12

    foot = f"{variant_label} · {width}×{height}"
    fb = draw.textbbox((0, 0), foot, font=sub_font)
    fw = fb[2] - fb[0]
    draw.text(((width - fw) // 2, height - margin - (fb[3] - fb[1])), foot, font=sub_font, fill=(160, 165, 180))

    img.save(output_path, "PNG", optimize=True)
    return output_path.resolve()


def main() -> None:
    import argparse

    from game_library import list_games

    game_choices = list_games()
    p = argparse.ArgumentParser(description="生成 9:16 竖版视频封面（本地图库底图 + 标题）")
    p.add_argument("--title", "-t", required=True, help="视频标题，可用 \\n 换行")
    p.add_argument(
        "--game",
        "-g",
        required=True,
        choices=game_choices,
        metavar="GAME",
        help="游戏（与 game_library.py 中配置一致）",
    )
    p.add_argument("--output", "-o", default="cover.png", help="输出 PNG 路径")
    args = p.parse_args()
    title = args.title.replace("\\n", "\n")
    path = generate_cover(title, args.game, args.output)
    print(f"已保存: {path}")


if __name__ == "__main__":
    main()
