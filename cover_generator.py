"""
竖版 9:16 视频封面生成：标题 + 游戏名；底图来自本地 assets/games/ 图库。
"""
from __future__ import annotations

import hashlib
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from game_library import background_path_for_game

# 9:16 竖版，常用短视频规格
WIDTH = 1080
HEIGHT = 1920


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


def _windows_font_candidates(bold: bool) -> list[Path]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    fonts = Path(windir) / "Fonts"
    regular = [fonts / "msyh.ttc", fonts / "simhei.ttf", fonts / "simsun.ttc"]
    bold_faces = [fonts / "msyhbd.ttc", fonts / "msyh.ttc"]
    return bold_faces if bold else regular


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _windows_font_candidates(bold):
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size, index=0)
            except OSError:
                continue
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
    """先画黑描边，再画白描边，最后填充主色。"""
    if not text:
        return
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = center_x - tw // 2

    # 外黑描边（粗）
    draw.text(
        (tx, top_y),
        text,
        font=font,
        fill=fill,
        stroke_width=10,
        stroke_fill=(0, 0, 0),
    )
    # 内白描边（细），提升亮度与可读性
    draw.text(
        (tx, top_y),
        text,
        font=font,
        fill=fill,
        stroke_width=4,
        stroke_fill=(245, 245, 245),
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

    title_font = _load_font(102, bold=True)
    line1, line2 = _title_two_lines(title)
    start_y = int(height * 0.23)
    line_gap = 118

    # 第一行：高饱和蓝；第二行：高饱和黄，接近常见短视频故障排查封面风格
    _draw_center_text_with_outline(
        draw,
        line1,
        center_x=width // 2,
        top_y=start_y,
        font=title_font,
        fill=(55, 150, 255),
    )
    _draw_center_text_with_outline(
        draw,
        line2,
        center_x=width // 2,
        top_y=start_y + line_gap,
        font=title_font,
        fill=(255, 220, 45),
    )

    base = base.convert("RGB")
    base = base.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))

    base.save(output_path, "PNG", optimize=True)
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
