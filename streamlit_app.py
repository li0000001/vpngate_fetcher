import streamlit as st
import pandas as pd
import requests
import io
import base64
import re

# 1. 设置网页标题和布局
st.set_page_config(page_title="VPN Gate 高级解析器", page_icon="🌐", layout="wide")
st.title("🌐 VPN Gate 实时节点高级解析器")
st.caption("已深度解析：包含端口、协议、并发、流量及在线时间等完整信息")

# 提取端口和协议的辅助函数
def extract_port_and_proto(base64_config):
    try:
        config_text = base64.b64decode(base64_config).decode('utf-8')
        # 寻找类似 "remote 11.22.33.44 1194" 的行提取端口
        remote_match = re.search(r'remote\s+\S+\s+(\d+)', config_text)
        # 寻找类似 "proto udp" 或 "proto tcp" 的行提取协议
        proto_match = re.search(r'proto\s+(\S+)', config_text)
        
        port = remote_match.group(1) if remote_match else "未知"
        proto = proto_match.group(1).upper() if proto_match else "UDP" # 默认通常是UDP
        return port, proto, config_text
    except:
        return "未知", "未知", ""

# 2. 数据抓取与清洗逻辑
if st.button("🔄 立即抓取最新节点", type="primary") or 'df_nodes' not in st.session_state:
    url = "https://www.vpngate.net/api/iphone/"
    
    with st.spinner("正在深度解析 vpngate.net 数据，请稍候..."):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            if len(lines) >= 4:
                csv_data = "\n".join(lines[1:-1])
                
                # 读取并处理 CSV 数据
                df = pd.read_csv(io.StringIO(csv_data))
                
                # 过滤掉没有配置文件的坏节点
                df = df.dropna(subset=['OpenVPN_ConfigData_Base64'])
                
                # 数据类型强制转换
                df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce')
                df['Ping'] = pd.to_numeric(df['Ping'], errors='coerce')
                df['NumVpnSessions'] = pd.to_numeric(df['NumVpnSessions'], errors='coerce')
                df['Uptime'] = pd.to_numeric(df['Uptime'], errors='coerce')
                df['TotalTraffic'] = pd.to_numeric(df['TotalTraffic'], errors='coerce')
                
                # 【核心修复】动态解析出每行数据隐藏的端口和协议，并存为新列
                ports = []
                protos = []
                configs = []
                for _, row in df.iterrows():
                    p, pt, conf = extract_port_and_proto(row['OpenVPN_ConfigData_Base64'])
                    ports.append(p)
                    protos.append(pt)
                    configs.append(conf)
                
                df['服务端口'] = ports
                df['传输协议'] = protos
                df['Decoded_Config'] = configs  # 顺便把解密后的文本缓存起来
                
                # 按网速降序排序
                df_sorted = df.sort_values(by='Speed', ascending=False)
                
                # 单位转换
                df_sorted['Speed (Mbps)'] = round(df_sorted['Speed'] / 1024 / 1024, 2)
                df_sorted['总流量 (GB)'] = round(df_sorted['TotalTraffic'] / 1024 / 1024 / 1024, 2)
                df_sorted['在线时间 (天)'] = round(df_sorted['Uptime'] / 1000 / 60 / 60 / 24, 1)
                
                # 存入 Session 缓存
                st.session_state['df_nodes'] = df_sorted
                st.success("✅ 全量数据抓取并深度解析成功！")
            else:
                st.error("❌ 官方返回的数据格式有误。")
        except Exception as e:
            st.error(f"❌ 抓取失败！错误信息: {e}")

# 3. 页面渲染逻辑
if 'df_nodes' in st.session_state:
    df_display = st.session_state['df_nodes']
    
    # --- 模块一：全局统计仪表盘 ---
    st.subheader("📈 实时网络概览")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric(label="当前可用节点总数", value=len(df_display))
    kpi1.caption("所有节点均包含 OpenVPN 配置文件")
    
    max_speed = df_display['Speed (Mbps)'].max() if not df_display.empty else 0
    kpi2.metric(label="全网最高带宽", value=f"{max_speed} Mbps")
    kpi2.caption("来自最快志愿者的网络节点")
    
    top_country = df_display['CountryLong'].value_counts().idxmax() if not df_display.empty else "未知"
    kpi3.metric(label="节点最多国家/地区", value=top_country)
    kpi3.caption("当前该地区的志愿者在线数量最多")
    
    st.markdown("---")

    # --- 模块二：精选 Top 3 节点的详细卡片 ---
    st.subheader("📥 热门节点详细档案 & 配置文件下载（Top 3）")
    top_nodes = df_display.head(3)
    
    cols = st.columns(3)
    for idx, (index, row) in enumerate(top_nodes.iterrows()):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"### 🏆 排名 #{idx+1} · {row['CountryLong']}")
                st.markdown(f"**基本网络配置：**")
                st.write(f"🌐 **IP 地址:** `{row['IP']}`")
                st.write(f"🚪 **服务端口:** `{row['服务端口']}`")
                st.write(f"🔌 **传输协议:** `{row['传输协议']}`")
                st.write(f"🏢 **运营商:** `{row['Operator']}`")
                
                st.markdown("**网络质量：**")
                st.write(f"⚡ **带宽速度:** `{row['Speed (Mbps)']} Mbps`")
                st.write(f"⏱️ **Ping 延迟:** `{row['Ping']} ms`")
                
                st.markdown("**运行状态：**")
                st.write(f"👥 **当前活跃连接:** `{int(row['NumVpnSessions'])}` 人")
                st.write(f"⏳ **连续在线时间:** `{row['在线时间 (天)']} 天`")
                st.write(f"📊 **累计消耗流量:** `{row['总流量 (GB)']} GB`")
                
                # 下载按钮（直接读取我们刚才解密并存好的文本）
                if row['Decoded_Config']:
                    st.download_button(
                        label=f"📥 下载该节点 .ovpn 配置文件",
                        data=row['Decoded_Config'],
                        file_name=f"vpngate_{row['IP']}_{row['服务端口']}.ovpn",
                        mime="application/x-openvpn-profile",
                        key=f"dl_card_{index}",
                        use_container_width=True
                    )
                else:
                    st.error("配置文件不可用")

    st.markdown("---")

    # --- 模块三：全量数据大表 ---
    st.subheader("📊 全量节点详细数据矩阵（支持动态交互）")
    st.caption("你可以点击任意表头进行升序/降序排列，或点击右上角放大查看全表")
    
    full_table_df = df_display[[
        'CountryLong', 'IP', '服务端口', '传输协议', 'Speed (Mbps)', 'Ping', 
        'NumVpnSessions', '在线时间 (天)', '总流量 (GB)', 'Operator'
    ]].copy()
    
    st.dataframe(
        full_table_df, 
        column_config={
            "CountryLong": "国家/地区",
            "IP": "IP 地址",
            "服务端口": "服务端口",
            "传输协议": "协议 (TCP/UDP)",
            "Speed (Mbps)": "带宽网速 (Mbps)",
            "Ping": "延迟 (ms)",
            "NumVpnSessions": "当前在线人数",
            "在线时间 (天)": "稳定运行时间",
            "总流量 (GB)": "累计传输流量",
            "Operator": "节点所有者 (ISP)"
        },
        use_container_width=True,
        height=500
    )
