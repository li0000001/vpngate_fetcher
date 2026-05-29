import pandas as pd
import requests
import io
import base64

def fetch_and_parse_vpngate():
    # 1. VPN Gate 官方公开的实时 CSV 数据接口
    url = "https://www.vpngate.net/api/iphone/"
    
    print("正在从 vpngate.net 抓取最新节点列表，请稍候...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 抓取失败，请检查网络连接或代理设置。错误信息: {e}")
        return

    # 2. 清洗数据：VPN Gate 返回的前两行是版权声明，最后一行是感叹号，需要剔除
    lines = response.text.splitlines()
    if len(lines) < 4:
        print("❌ 获取到的数据格式不正确。")
        return
        
    # 保留核心的 CSV 数据行
    csv_data = "\n".join(lines[1:-1])

    # 3. 使用 pandas 解析 CSV 数据
    # 字段包含：HostName, IP, Score, Ping, Speed, CountryLong, OpenVPN_ConfigData_Base64 等
    df = pd.read_csv(io.StringIO(csv_data))

    # 4. 数据类型转换与排序（将速度和延迟转为数字，按分数/速度降序排列）
    df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce')
    df['Ping'] = pd.to_numeric(df['Ping'], errors='coerce')
    
    # 筛选出含有 OpenVPN 配置且速度不为空的节点，并按速度从大到小排序
    df_sorted = df.dropna(subset=['OpenVPN_ConfigData_Base64', 'Speed']).sort_values(by='Speed', ascending=False)

    # 5. 输出前 3 个最优节点的信息
    top_n = 3
    print(f"\n======== 已为您筛选出速度最快的前 {top_n} 个节点 ========\n")
    
    for index, row in df_sorted.head(top_n).iterrows():
        # 转换网速单位 (bps -> Mbps)
        speed_mbps = round(row['Speed'] / 1024 / 1024, 2)
        
        print(f"【节点 #{index + 1}】")
        print(f"国家/地区: {row['CountryLong']}")
        print(f"IP 地址:   {row['IP']}")
        print(f"Ping 延迟: {row['Ping']} ms")
        print(f"当前网速:  {speed_mbps} Mbps")
        
        # 解码 OpenVPN 配置文件文本
        try:
            ovpn_config = base64.b64decode(row['OpenVPN_ConfigData_Base64']).decode('utf-8')
            # 打印配置文件的片段（前 3 行示范）
            config_preview = "\n".join(ovpn_config.splitlines()[:3])
            print(f"配置预览:\n{config_preview}\n  ... (此处省略其余配置代码) ...")
        except Exception:
            print("配置文件解码失败")
            
        print("-" * 50)

if __name__ == "__main__":
    fetch_and_parse_vpngate()
