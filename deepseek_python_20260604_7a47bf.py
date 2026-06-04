import streamlit as st
import pandas as pd
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------- 初始化 ----------
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.seq = 0
    st.session_state.last_time = None
    st.session_state.records = []   # 每个元素为 (序号, 时间戳浮点数)
    st.session_state.alert = ""

def add_record(seq, ts):
    st.session_state.records.insert(0, (seq, ts))
    if len(st.session_state.records) > 20:
        st.session_state.records.pop()
    st.session_state.seq = seq
    st.session_state.last_time = ts

def reset():
    st.session_state.running = False
    st.session_state.seq = 0
    st.session_state.last_time = None
    st.session_state.records = []
    st.session_state.alert = ""

# ---------- 自动刷新 ----------
if st.session_state.running:
    st_autorefresh(interval=1000, key="auto")

# ---------- 界面 ----------
st.title("🛸 无人机心跳监测系统")
st.markdown("每秒模拟一个心跳，超时3秒报警，实时折线图+表格")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("启动模拟"):
        reset()
        st.session_state.running = True
        now = time.time()
        add_record(1, now)
with c2:
    if st.button("暂停/恢复"):
        st.session_state.running = not st.session_state.running
with c3:
    if st.button("停止模拟"):
        reset()

# ---------- 心跳生成（运行中才执行）----------
if st.session_state.running:
    now = time.time()
    last = st.session_state.last_time
    if last is None:
        now = time.time()
        add_record(1, now)
    else:
        diff = now - last
        if diff >= 1.0:
            n = min(int(diff), 5)   # 补偿最多5个
            for i in range(n):
                new_seq = st.session_state.seq + 1
                sim_ts = last + (i + 1)
                add_record(new_seq, sim_ts)

    # 超时报警
    if st.session_state.last_time and (time.time() - st.session_state.last_time) > 3.0:
        st.session_state.alert = f"⚠️ 连接超时！已 {time.time() - st.session_state.last_time:.1f} 秒未收到心跳"
    else:
        st.session_state.alert = ""

# ---------- 状态展示 ----------
colA, colB = st.columns(2)
with colA:
    st.metric("最新心跳序号", st.session_state.seq if st.session_state.seq > 0 else "—")
    status = "✈️ 飞行中" if st.session_state.running else "🛑 已停止"
    st.write(f"无人机状态：{status}")
with colB:
    if st.session_state.alert:
        st.error(st.session_state.alert)
    else:
        st.success("✅ 连接正常")

# ---------- 折线图 ----------
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records, columns=["序号", "时间戳"])
    df["时间"] = pd.to_datetime(df["时间戳"], unit="s")
    df = df.sort_values("时间")  # 按时间正序绘图
    st.subheader("📈 心跳序号变化趋势")
    st.line_chart(df.set_index("时间")["序号"])
else:
    st.info("尚未收到任何心跳包，请点击「启动模拟」")

# ---------- 表格 ----------
if st.session_state.records:
    df_table = pd.DataFrame(st.session_state.records, columns=["心跳序号", "时间戳"])
    df_table["接收时间"] = df_table["时间戳"].apply(lambda x: datetime.fromtimestamp(x).strftime("%H:%M:%S"))
    df_table = df_table[["心跳序号", "接收时间"]]
    st.subheader("📋 心跳包记录（最近20条）")
    st.dataframe(df_table, use_container_width=True)
else:
    st.info("暂无记录")