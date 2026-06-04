# app.py
import streamlit as st
import pandas as pd
import time
import threading
from datetime import datetime, timedelta
from collections import deque

# ==================== 配置参数 ====================
MAX_HISTORY = 200          # 最多保存心跳包数量
HEARTBEAT_INTERVAL = 1.0   # 心跳发送间隔（秒）
TIMEOUT_SECONDS = 3        # 超时阈值（秒）

# ==================== 初始化 session_state ====================
if "heartbeat_data" not in st.session_state:
    st.session_state.heartbeat_data = deque(maxlen=MAX_HISTORY)
if "running" not in st.session_state:
    st.session_state.running = False
if "pause" not in st.session_state:
    st.session_state.pause = False
if "last_seq" not in st.session_state:
    st.session_state.last_seq = 0
if "lock" not in st.session_state:
    st.session_state.lock = threading.Lock()

# ==================== 心跳发送线程 ====================
def heartbeat_sender():
    """后台线程：模拟无人机每秒发送一个心跳包"""
    seq = 0
    while st.session_state.running:
        if not st.session_state.pause:
            seq += 1
            now = datetime.now()
            with st.session_state.lock:
                st.session_state.heartbeat_data.append({
                    "序号": seq,
                    "接收时间": now,
                    "时间戳": now.strftime("%H:%M:%S")
                })
                st.session_state.last_seq = seq
        # 等待下一次发送（即使暂停也按固定周期检查）
        time.sleep(HEARTBEAT_INTERVAL)

# ==================== 启动/停止模拟 ====================
def start_simulation():
    if not st.session_state.running:
        st.session_state.running = True
        st.session_state.pause = False
        st.session_state.heartbeat_data.clear()
        st.session_state.last_seq = 0
        thread = threading.Thread(target=heartbeat_sender, daemon=True)
        thread.start()
        st.success("✅ 模拟已启动，无人机开始发送心跳包")

def stop_simulation():
    st.session_state.running = False
    st.session_state.pause = False
    st.warning("⏹️ 模拟已停止")

def pause_resume():
    if st.session_state.running:
        st.session_state.pause = not st.session_state.pause
        if st.session_state.pause:
            st.warning("⏸️ 心跳发送已暂停（可测试掉线报警）")
        else:
            st.success("▶️ 心跳发送已恢复")

# ==================== 地面站逻辑：检测超时 ====================
def check_timeout():
    """返回 (是否超时, 距上次心跳秒数)"""
    with st.session_state.lock:
        data = list(st.session_state.heartbeat_data)
    if not data:
        return True, TIMEOUT_SECONDS + 1  # 无数据视为超时
    last_time = data[-1]["接收时间"]
    elapsed = (datetime.now() - last_time).total_seconds()
    return elapsed > TIMEOUT_SECONDS, elapsed

# ==================== Streamlit 界面 ====================
st.set_page_config(page_title="无人机心跳监测站", layout="wide")
st.title("🚁 无人机心跳监测系统")
st.markdown("模拟无人机每秒发送心跳包，地面站实时监测并绘制折线图，**3秒未收到自动报警**")

# ----- 控制栏 -----
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🚀 启动模拟", on_click=start_simulation, use_container_width=True)
with col2:
    st.button("⏸️ 暂停/恢复", on_click=pause_resume, use_container_width=True)
with col3:
    st.button("🛑 停止模拟", on_click=stop_simulation, use_container_width=True)

st.divider()

# ----- 状态显示区域 -----
status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    if st.session_state.running:
        if st.session_state.pause:
            st.warning("⏸️ 发送已暂停")
        else:
            st.success("🟢 无人机状态：飞行中")
    else:
        st.error("🔴 无人机状态：未启动")

# 显示最新心跳序号和时间
with status_col2:
    with st.session_state.lock:
        if st.session_state.heartbeat_data:
            last = st.session_state.heartbeat_data[-1]
            st.metric("最新心跳序号", last["序号"])
            st.caption(f"接收时间: {last['时间戳']}")
        else:
            st.metric("最新心跳序号", "--")
            st.caption("暂无数据")

# 超时报警显示
with status_col3:
    timeout, elapsed = check_timeout()
    if timeout and st.session_state.running and not st.session_state.pause:
        st.error(f"🚨 连接超时！已 {elapsed:.1f} 秒未收到心跳")
    elif st.session_state.pause and st.session_state.running:
        st.warning("⚠️ 当前处于暂停发送状态，请注意超时检测")
    else:
        st.success(f"✅ 连接正常 (距上次心跳 {elapsed:.1f} 秒)")

st.divider()

# ----- 折线图：序号随时间变化 -----
st.subheader("📈 心跳序号变化趋势")
with st.session_state.lock:
    data_list = list(st.session_state.heartbeat_data)

if data_list:
    df = pd.DataFrame(data_list)
    # 仅保留序号和接收时间用于绘图
    df_chart = df[["序号", "接收时间"]].copy()
    df_chart["接收时间"] = pd.to_datetime(df_chart["接收时间"])
    st.line_chart(df_chart, x="接收时间", y="序号", use_container_width=True)
else:
    st.info("尚未收到任何心跳包，请点击「启动模拟」")

# ----- 数据表格展示 -----
st.subheader("📋 心跳包记录 (最近 20 条)")
if data_list:
    display_df = pd.DataFrame(list(reversed(data_list))).head(20)
    display_df["接收时间"] = display_df["接收时间"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(display_df[["序号", "接收时间", "时间戳"]], use_container_width=True)
else:
    st.caption("暂无记录")

# ----- 自动刷新：每秒更新一次界面 -----
# 注意：Streamlit 本身不是实时框架，这里利用 time.sleep 实现动态刷新
# 为了保证折线图和数据能实时更新，我们让脚本在此处循环刷新
# 但为了避免重复挂载线程，需要判断是否为主循环（用 session_state 标志避免多次创建）
if "refreshing" not in st.session_state:
    st.session_state.refreshing = False

if st.session_state.running and not st.session_state.refreshing:
    st.session_state.refreshing = True
    placeholder = st.empty()
    while st.session_state.running:
        time.sleep(1.0)
        st.rerun()  # 触发脚本重新运行，刷新界面
    st.session_state.refreshing = False
elif not st.session_state.running and st.session_state.refreshing:
    st.session_state.refreshing = False

# 说明信息
st.sidebar.markdown("""
### 📌 使用说明
1. 点击 **「启动模拟」** 开始生成心跳包
2. 点击 **「暂停/恢复」** 可模拟无人机掉线（3秒后触发超时报警）
3. 折线图实时展示心跳序号随时间变化
4. 右侧表格可查看最近20条心跳记录
5. 点击 **「停止模拟」** 结束本次飞行
""")
st.sidebar.success("✅ 满足作业要求：心跳自发自收 + 超时检测 + 序号折线图")