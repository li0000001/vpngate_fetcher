import streamlit as st
import pandas as pd
import requests
import io
import base64

# 1. 设置网页标题和图标
st.set_page_config(page_title="VPN Gate 节点抓取器", page_icon="🌐", layout="wide")
st.title("🌐 VPN Gate 实时节点抓取与解析器")
st.caption("数据实时同步自日本筑波大学 VPN Gate 官方公开接口")

# 2. 放置一个刷新按钮
if st.button("🔄 立即抓取最新节点", type="primary") or 'df_nodes' not in st.session_state:
    
    url = "https://www.vpngate.net/api/iphone/"
    
    with st.spinner("正在从 vpngate.net 抓取并解析数据，请稍候..."):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # 清洗 CSV 数据
            lines = response.text.splitlines()
            if len(lines) >= 4:
                csv_data = "\n".join(lines[1:-1])
                
                # 用 Pandas 处理
                df = pd.read_csv(io.StringIO(csv_data))
                df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce')
                df['Ping'] = pd.to_numeric(df['Ping'], errors='coerce')
                
                # 过滤并按网速排序
                df_sorted = df.dropna(subset=['OpenVPN_ConfigData_Base64', 'Speed']).sort_values(by='Speed', ascending=False)
                
                # 将网速单位转换为 Mbps
                df_sorted['Speed (Mbps)'] = round(df_sorted['Speed'] / 1024 / 1024, 2)
                
                # 存入 session_state 缓存
                st.session_state['df_nodes'] = df_sorted
                st.success("✅ 数据抓取成功！")
            else:
                st.error("❌ 官方返回的数据格式有误。")
        except Exception as e:
            st.error(f"❌ 抓取失败！可能 Streamlit 服务器目前无法连接到 vpngate.net。错误信息: {e}")

# 3. 渲染数据到网页
if 'df_nodes' in st.session_state:
    df_display = st.session_state['df_nodes']
    
    # 展示核心数据表格
    st.subheader("📊 节点概览（已按网速降序排列）")
    st.dataframe(
        df_display[['CountryLong', 'IP', 'Speed (Mbps)', 'Ping', 'Operator']], 
        column_config={
            "CountryLong": "国家/地区",
            "IP": "IP 地址",
            "Speed (Mbps)": "网速 (Mbps)",
            "Ping": "延迟 (ms)",
            "Operator": "提供者"
        },
        use_container_width=True
    )
    
    # 允许查看详情并下载配置文件
    st.subheader("📥 热门节点配置文件下载（Top 3）")
    top_nodes = df_display.head(3)
    
    cols = st.columns(3)
    for idx, (index, row) in enumerate(top_nodes.iterrows()):
        with cols[idx]:
            st.info(f"**排名 #{idx+1}：{row['CountryLong']}**")
            st.write(f"📍 IP: `{row['IP']}`")
            st.write(f"⚡ 网速: `{row['Speed (Mbps)']} Mbps` | ⏱️ 延迟: `{row['Ping']} ms`")
            
            # 解码并转换为下载按钮
            try:
                ovpn_config = base64.b64decode(row['OpenVPN_ConfigData_Base64']).decode('utf-8')
                st.download_button(
                    label=f"📥 下载 .ovpn 配置文件",
                    data=ovpn_config,
                    file_name=f"vpngate_{row['IP']}.ovpn",
                    mime="application/x-openvpn-profile",
                    key=f"dl_{index}"
                )
            except:
                st.write("配置文件解析失败")
