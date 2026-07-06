import os
import httpx
from dotenv import load_dotenv

# 确保加载 .env 文件中的环境变量
load_dotenv()

def get_realtime_news(query: str = "今日热点") -> str:
    """
    获取实时新闻或热搜（使用稳定正规的 天行数据 API）
    """
    if not query:
        query = "今日热点"
        
    # 从环境变量中读取天行数据的 Key
    api_key = os.getenv("TIANAPI_KEY")
    if not api_key:
        return "系统未配置天行数据 API Key，请在 .env 文件中添加 TIANAPI_KEY。"
        
    # 天行数据的微博热搜接口
    # url = f"https://apis.tianapi.com/weibohot/index?key={api_key}"

    # 国际热点新闻
    url = f"https://apis.tianapi.com/world/index?key={api_key}"
    
    try:
        # 正规 API 不需要伪装头，直接请求
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            # 天行数据接口成功的状态码通常是 200
            if data.get('code') == 200:
                # 提取前 5 条热点
                items = data.get('result', {}).get('list', [])[:5]
                lines = []
                for i, item in enumerate(items, start=1):
                    title = item.get('hotword', '')
                    hot_value = item.get('hotwordnum', '未知')
                    lines.append(f"{i}. {title} (热度: {hot_value})")
                
                return f"【实时资讯/热点获取成功】\n" + "\n".join(lines) + "\n请根据以上内容自然地回复用户。"
            else:
                # 打印 API 返回的具体错误信息，方便排查（例如额度用完、未申请接口等）
                error_msg = data.get('msg', '未知错误')
                print(f"[News Skill Warning]: API 返回异常 - {error_msg}")
                return f"抱歉，暂时无法获取最新资讯数据，原因：{error_msg}。"
                
    except Exception as e:
        error_msg = str(e)
        print(f"[News Skill Error]: {error_msg}")
        return f"获取实时新闻失败，网络请求异常：{error_msg}。"