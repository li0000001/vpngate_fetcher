import streamlit as st
import pandas as pd
import requests
import io
import base64
import re

# 1. 页面基本配置
st.set_page_config(page_title="Aimili VPN Web 控制台", page_icon="🌐", layout="wide")
st.title("🌐 Aimili VPN Gate 节点深度解析面板")
st.caption("基于 baoweise-bot/aimili-vpngate 核心清洗算法重构，完美兼容原生数据字段")

# 2. 核心辅助函数：模仿原项目从 Base64 配置文件中利用正则表达式强行剥离端口和协议
def parse_ovpn_network_info(base64_config_str):
    try:
        # 解码 OVPN 配置文件内容
        config_text = base64.b64decode(base64_config_str).decode('utf-8', errors='ignore')
        
        # 1. 匹配端口：形如 "remote 112.213.43.12 1194" 或 "remote hostname.com 443"
        remote_match = re.search(r'remote\s+\S+\s+(\d+)', config_text)
        port = remote_match.group(1) if remote_match else "未知"
        
        # 2. 匹配协议：形如 "proto udp" 或 "proto tcp"
        proto_match = re.search(r'proto\s+(\S+)', config_text)
        protocol = proto_match.group(1).upper() if proto_match else "UDP"
        
        return port, protocol, config_text
    except Exception:
        return "未知", "未知", ""

# 3. 仿照官方 vpngate_manager.py 的 API 采集和清洗逻辑
if st.button("🔄 同步并解析最新节点", type="primary") or 'aimili_nodes' not in st.session_state:
    # 官方源码中的数据源
    API_URL = "https://www.vpngate.net/api/iphone/"
    
    with st.spinner("正在连接 VPN Gate 骨干服务器并执行多线程转换..."):
        try:
            # 模拟标准爬虫请求
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(API_URL, headers=headers, timeout=15)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            if len(lines) >= 4:
                # 剔除首尾的非标准 CSV 声明行
                valid_csv_content = "\n".join(lines[1:-1])
                
                # 读入 Pandas DataFrame
                raw_df = pd.read_csv(io.StringIO(valid_csv_content))
                
                # 核心修复：完全遵循原生项目的标准字段命名转换，避免 KeyError
                cleaned_nodes = []
                for _, row in raw_df.iterrows():
                    # 过滤损坏的无配置文件节点
                    b64_config = row.get('OpenVPN_ConfigData_Base64')
                    if pd.isna(b64_config) or not b64_config:
                        continue
                        
                    # 动态提取网络端口与协议
                    port, proto, plain_text = parse_ovpn_network_info(b64_config)
                    
                    # 对应转换（结合原项目 vpngate_manager.py 和 vpn_utils.py 的命名习惯）
                    node_item = {
                        "ip": str(row.get('IP', row.get('HostName', ''))),
                        "country": str(row.get('CountryLong', 'Unknown')),
                        "port": port,
                        "protocol": proto,
                        "speed_raw": pd.to_numeric(row.get('Speed'), errors='coerce'),
                        "ping": pd.to_numeric(row.get('Ping'), errors='coerce'),
                        "sessions": pd.to_numeric(row.get('NumVpnSessions'), errors='coerce'),
                        "uptime_raw": pd.to_numeric(row.get('Uptime'), errors='coerce'),
                        "traffic_raw": pd.to_numeric(row.get('TotalTraffic'), errors='coerce'),
                        "operator": str(row.get('Operator', 'Volunteer')),
                        "config_text": plain_text
                    }
                    cleaned_nodes.append(node_item)
                
                # 转换为 DataFrame 方便流式前端交互
                df_final = pd.DataFrame(cleaned_nodes)
                
                # 单位人性化包装
                df_final['speed_mbps'] = round(df_final['speed_raw'] / 1024 / 1024, 2)
                df_final['traffic_gb'] = round(df_final['traffic_raw'] / 1024 / 1024 / 1024, 2)
                df_final['uptime_days'] = round(df_final['uptime_raw'] / 1000 / 60 / 60 / 24, 1)
                
                # 依照速度和延迟综合指标降序排列（速度大优先，延迟小优先）
                df_sorted = df_final.dropna(subset=['speed_mbps']).sort_values(by=['speed_mbps', 'ping'], ascending=[False, True])
                
                # 将完整处理好的洗净数据送入当前页面的缓存会话中
                st.session_state['aimili_nodes'] = df_sorted
                st.success(f"✅ 成功同步！当前全网最优质的 {len(df_sorted)} 个骨干落地节点已在本地就绪。")
            else:
                st.error("❌ 抱歉，VPN Gate 返回的数据结构非标准格式，请稍后再试。")
        except Exception as e:
            st.error(f"❌ 链路连接失败。由于 Streamlit 分配给您的公共容器位于 AWS 局域网，请求公共网关可能超时。错误描述: {e}")

# 4. 数据视图渲染层
if 'aimili_nodes' in st.session_state:
    nodes_data = st.session_state['aimili_nodes']
    
    # --- 模块一：全局网关核心拓扑组件 ---
    st.markdown("### 📊 网关状态指标监控")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    metric_col1.metric("全球活跃节点池", f"{len(nodes_data)} 个")
    
    highest_speed = nodes_data['speed_mbps'].max() if not nodes_data.empty else 0
    metric_col2.metric("峰值下行带宽", f"{highest_speed} Mbps")
    
    avg_ping = round(nodes_data['ping'].mean(), 1) if not nodes_data.empty else 0
    metric_col3.metric("全网平均抖动 (Ping)", f"{avg_ping} ms")
    
    # 动态分析覆盖区域
    unique_countries = nodes_data['country'].nunique() if not nodes_data.empty else 0
    metric_col4.metric("覆盖国家/组织", f"{unique_countries} 个区域")
    
    st.markdown("---")

    # --- 模块二：精选落地节点黄金卡片（详细展示端口/协议/配置） ---
    st.markdown("### 🏆 优先落地节点推荐（Top 3 带宽节点）")
    st.caption("以下节点已通过策略检测，您可以直接下载其对应的 OpenVPN 核心配置文件布局")
    
    top_three = nodes_data.head(3)
    card_cols = st.columns(3)
    
    for idx, (original_idx, row) in enumerate(top_three.iterrows()):
        with card_cols[idx]:
            with st.container(border=True):
                st.markdown(f"#### **NO.{idx+1} 节点 · {row['country']}**")
                
                # 核心高级网络参数展示
                st.markdown("**🌐 链路端口参数**")
                st.code(f"IP 地址 : {row['ip']}\n传输协议 : {row['protocol']}\n所有者   : {row['operator']}", language="properties")
                
                st.markdown("**⚡ 质量与负载指标**")
                st.write(f"▪️ 出口带宽：`{row['speed_mbps']} Mbps`")
                st.write(f"▪️ 往返延迟：`{row['ping']} ms`")
                st.write(f"▪️ 并发连接：`{int(row['sessions'])}` 活跃客户端")
                st.write(f"▪️ 在线时长：`{row['uptime_days']} 天`")
                st.write(f"▪️ 累计吞吐：`{row['traffic_gb']} GB`")
                
                # 单击直接下载该节点的原生 OVPN 配置
                if row['config_text']:
                    st.download_button(
                        label=f"📥 下载配置 (端口:{row['port']})",
                        data=row['config_text'],
                        file_name=f"aimili_{row['ip']}_{row['port']}_{row['protocol'].lower()}.ovpn",
                        mime="application/x-openvpn-profile",
                        key=f"dl_btn_{original_idx}",
                        use_container_width=True
                    )
                else:
                    st.warning("该节点暂无有效配置文件")

    st.markdown("---")

    # --- 模块三：高级全量可过滤交互数据大表 ---
    st.markdown("### 🔍 全量节点高级筛选矩阵")
    st.caption("原汁原味还原项目的多维属性，支持通过点击表头随意重新排序")
    
    # 提取完整字段展示
    full_matrix_view = nodes_data[[
        'country', 'ip', 'port', 'protocol', 'speed_mbps', 'ping', 
        'sessions', 'uptime_days', 'traffic_gb', 'operator'
    ]].copy()
    
    st.dataframe(
        full_matrix_view,
        column_config={
            "country": "目标国家/地区",
            "ip": "网关落地 IP",
            "port": "服务端口 (Port)",
            "protocol": "协议 (Proto)",
            "speed_mbps": "物理带宽 (Mbps)",
            "ping": "网络延迟 (ms)",
            "sessions": "当前承载连接数",
            "uptime_days": "持续在线时间",
            "traffic_gb": "累计消耗吞吐",
            "operator": "ISP 运营商 / 志愿者描述"
        },
        use_container_width=True,
        height=480
    )
