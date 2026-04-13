"""
本地网页：输入标题与游戏名，生成 9:16 竖版封面；支持同文案生成横图+竖图占位图（后续可替换实现）。
运行: streamlit run streamlit_app.py
"""
from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import streamlit as st

from cover_generator import (
    HEIGHT,
    HORIZONTAL_HEIGHT,
    HORIZONTAL_WIDTH,
    WIDTH,
    generate_cover,
    generate_cover_horizontal,
)
from game_library import background_path_for_game, list_games

# 竖图缩略宽度（像素）；越小越省纵向空间，便于一屏看完两排十个
GAME_THUMB_WIDTH = 72

_COMPACT_CSS = """
<style>
    :root {
        --muted: rgba(120, 120, 130, 0.9);
    }
    .block-container {
        /* Cloud 托管页面有顶栏时，预留更大的顶部安全区 */
        padding-top: calc(1.2rem + env(safe-area-inset-top, 0px)) !important;
        padding-bottom: 0.8rem !important;
        max-width: 1260px !important;
    }
    /* 更紧凑的整体排版 */
    [data-testid="stMarkdownContainer"] p { margin-bottom: 0.4rem; }
    small, .muted { color: var(--muted); }

    /* 结果区图片：限制高度，避免撑爆页面 */
    .result-card {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .result-media {
        width: 100%;
        border-radius: 12px;
        overflow: hidden;
        background: rgba(40, 42, 50, 0.55);
        border: 1px solid rgba(120, 120, 130, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .result-media.h { height: 220px; }
    .result-media.v { height: 520px; }
    .result-media img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }
    .result-meta {
        font-size: 0.82rem;
        color: var(--muted);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }
    .result-meta code {
        font-size: 0.78rem;
        padding: 0.1rem 0.3rem;
    }

    /* 游戏卡片：更像“可选项”，减少占用空间 */
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stImage"] img {
        max-height: 92px !important;
        width: auto !important;
        object-fit: cover !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
        border-radius: 10px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaption"] {
        font-size: 0.78rem !important;
        line-height: 1.2 !important;
        margin-top: 0.15rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] button {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
        min-height: 1.9rem !important;
        font-size: 0.82rem !important;
    }
</style>
"""

def _b64_png(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")


def _render_result_card(*, kind: str, title: str, size_text: str, filename: str, png_bytes: bytes) -> None:
    """
    kind: 'h' | 'v'
    """
    b64 = _b64_png(png_bytes)
    with st.container(border=True):
        st.markdown(
            f"""
<div class="result-card">
  <div class="result-media {kind}">
    <img src="data:image/png;base64,{b64}" alt="{title}">
  </div>
  <div class="result-meta">
    <div><strong>{title}</strong> <span class="muted">{size_text}</span></div>
    <div><code>{filename}</code></div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.download_button(
            "下载 PNG",
            data=png_bytes,
            file_name=filename,
            mime="image/png",
            use_container_width=True,
        )


def _run_generate(title: str, game: str, out_name: str) -> None:
    try:
        with tempfile.TemporaryDirectory() as td:
            req = (out_name or "cover.png").strip()
            req_path = Path(req)
            stem = (req_path.stem or "cover").strip()

            v_path = Path(td) / (req_path.name or "cover.png")
            if v_path.suffix.lower() not in {".png", ".PNG"}:
                v_path = v_path.with_suffix(".png")

            h_path = Path(td) / f"{stem}_horizontal.png"
            if h_path.suffix.lower() not in {".png", ".PNG"}:
                h_path = h_path.with_suffix(".png")

            # 同一游戏：同时生成横图 + 竖图（两张底图分别来自不同目录）
            generate_cover(title.strip(), game.strip(), v_path)
            generate_cover_horizontal(title.strip(), game.strip(), h_path)

            v_bytes = v_path.read_bytes()
            h_bytes = h_path.read_bytes()

        # 存进 session，便于刷新/改选后仍能展示上次结果
        st.session_state.generated = {
            "h_bytes": h_bytes,
            "v_bytes": v_bytes,
            "h_name": h_path.name,
            "v_name": v_path.name,
        }
        st.toast("已生成横图 + 竖图封面")
    except Exception as e:  # noqa: BLE001
        st.error(f"生成失败：{e}")


def _render_game_tile(game: str, tile_index: int) -> None:
    path = background_path_for_game(game)
    selected = st.session_state.get("selected_game") == game
    with st.container(border=selected):
        if path.is_file():
            st.image(str(path), width=GAME_THUMB_WIDTH)
        else:
            st.info("缺图", icon="⚠️")
        st.caption(game)
        if st.button("点选", key=f"pick_{tile_index}", use_container_width=True, type="primary" if selected else "secondary"):
            st.session_state.selected_game = game


st.set_page_config(page_title="视频封面生成", layout="wide")
st.markdown(_COMPACT_CSS, unsafe_allow_html=True)

st.title("视频封面生成器")
st.caption(f"竖图 {WIDTH}×{HEIGHT} · 横图 {HORIZONTAL_WIDTH}×{HORIZONTAL_HEIGHT}")

if "selected_game" not in st.session_state:
    st.session_state.selected_game = list_games()[0]

if "generated" not in st.session_state:
    st.session_state.generated = None

left, right = st.columns([0.92, 1.08], gap="large")

with left:
    st.subheader("输入")
    title = st.text_area("标题文本", placeholder="例如：十分钟带你上手", height=84)
    row_op = st.columns([1, 1])
    with row_op[0]:
        out_name = st.text_input("竖图文件名", value="cover.png")
        st.caption("横图会自动命名为 `*_horizontal.png`")
    with row_op[1]:
        st.markdown(" ")
        do_gen = st.button("生成（横+竖）", type="primary", use_container_width=True)

    st.divider()
    st.subheader("选择游戏")
    st.caption("点击卡片里的“点选”切换。")
    games = list_games()
    # 2×5 紧凑网格
    grid_a = st.columns(5, gap="small")
    for i in range(5):
        with grid_a[i]:
            _render_game_tile(games[i], i)
    grid_b = st.columns(5, gap="small")
    for i in range(5, 10):
        with grid_b[i - 5]:
            _render_game_tile(games[i], i)

    st.caption(f"当前选择：`{st.session_state.selected_game}`")

    if do_gen:
        if not (title or "").strip():
            st.warning("请填写标题。")
        else:
            _run_generate(title, st.session_state.selected_game, out_name)

with right:
    st.subheader("结果")
    gen = st.session_state.get("generated")
    if not gen:
        st.markdown('<div class="muted">尚未生成。左侧填写标题并点击“生成（横+竖）”。</div>', unsafe_allow_html=True)
    else:
        tab_h, tab_v = st.tabs(["横图（占位）", "竖图"])
        with tab_h:
            _render_result_card(
                kind="h",
                title="横图（占位）",
                size_text=f"{HORIZONTAL_WIDTH}×{HORIZONTAL_HEIGHT}",
                filename=gen["h_name"],
                png_bytes=gen["h_bytes"],
            )
        with tab_v:
            _render_result_card(
                kind="v",
                title="竖图",
                size_text=f"{WIDTH}×{HEIGHT}",
                filename=gen["v_name"],
                png_bytes=gen["v_bytes"],
            )

with st.expander("命令行", expanded=False):
    st.code(
        'python cover_generator.py -t "标题" -g "王者荣耀" -o out.png',
        language="bash",
    )
