"""
本地网页：输入标题与游戏名，生成 9:16 竖版封面。
运行: streamlit run streamlit_app.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from cover_generator import HEIGHT, WIDTH, generate_cover
from game_library import background_path_for_game, list_games

# 竖图缩略宽度（像素）；越小越省纵向空间，便于一屏看完两排十个
GAME_THUMB_WIDTH = 72

_COMPACT_CSS = """
<style>
    .block-container {
        /* Cloud 托管页面有顶栏时，预留更大的顶部安全区 */
        padding-top: calc(2.2rem + env(safe-area-inset-top, 0px)) !important;
        padding-bottom: 0.4rem !important;
        max-width: 1180px !important;
    }
    /* 带边框的游戏卡片内：限制竖图预览高度 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stImage"] img {
        max-height: 18vh !important;
        width: auto !important;
        object-fit: contain !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaption"] {
        font-size: 0.72rem !important;
        line-height: 1.1 !important;
        margin-top: 0.05rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] button {
        padding-top: 0.15rem !important;
        padding-bottom: 0.15rem !important;
        min-height: 1.85rem !important;
        font-size: 0.78rem !important;
    }
</style>
"""


def _run_generate(title: str, game: str, out_name: str) -> None:
    try:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / (out_name or "cover.png").strip()
            if path.suffix.lower() not in {".png", ".PNG"}:
                path = path.with_suffix(".png")
            generate_cover(title.strip(), game.strip(), path)
            img_bytes = path.read_bytes()
        st.image(img_bytes, caption=f"{WIDTH}×{HEIGHT}")
        st.download_button(
            "下载 PNG",
            data=img_bytes,
            file_name=path.name,
            mime="image/png",
        )
        st.success("生成完成，可点击下载。")
    except Exception as e:  # noqa: BLE001
        st.error(f"生成失败：{e}")


def _render_game_tile(game: str, tile_index: int) -> None:
    path = background_path_for_game(game)
    selected = st.session_state.get("selected_game") == game
    with st.container(border=selected):
        if path.is_file():
            st.image(str(path), width=GAME_THUMB_WIDTH)
        else:
            st.warning("缺图", icon="⚠️")
            st.caption("请放入图库")
        st.caption(game)
        if st.button("点选", key=f"pick_{tile_index}", use_container_width=True, type="primary" if selected else "secondary"):
            st.session_state.selected_game = game


st.set_page_config(page_title="视频封面生成", layout="wide")
st.markdown(_COMPACT_CSS, unsafe_allow_html=True)
# 额外顶部占位，避免某些浏览器/宿主容器把首个标题顶住
st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

st.title("竖版视频封面生成器")
st.caption(f"{WIDTH}×{HEIGHT}；底图 assets/games/")

if "selected_game" not in st.session_state:
    st.session_state.selected_game = list_games()[0]

st.caption("两排共十个 → 点 **点选**；占位游戏可在 game_library.py 改名并替换图片。")

title = st.text_area("标题文本", placeholder="例如：十分钟带你上手", height=56)

st.markdown("**选择游戏**")
games = list_games()
row_a = st.columns(5)
for i in range(5):
    with row_a[i]:
        _render_game_tile(games[i], i)
row_b = st.columns(5)
for i in range(5, 10):
    with row_b[i - 5]:
        _render_game_tile(games[i], i)

row_op = st.columns([1.2, 1, 1])
with row_op[0]:
    st.markdown(f"**当前：** `{st.session_state.selected_game}`")
with row_op[1]:
    out_name = st.text_input("下载文件名", value="cover.png")
with row_op[2]:
    do_gen = st.button("生成封面", type="primary", use_container_width=True)

if do_gen:
    if not (title or "").strip():
        st.warning("请填写标题。")
    else:
        _run_generate(title, st.session_state.selected_game, out_name)

with st.expander("命令行", expanded=False):
    st.code(
        'python cover_generator.py -t "标题" -g "王者荣耀" -o out.png',
        language="bash",
    )
