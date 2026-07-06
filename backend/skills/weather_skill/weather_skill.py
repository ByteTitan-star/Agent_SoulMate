import os
import httpx
from dotenv import load_dotenv

# 确保加载 .env 文件中的环境变量
load_dotenv()

def get_realtime_weather(city: str) -> str:
    """
    获取国内城市实时天气（使用和风天气专属 API Host）
    """
    if not city:
        return "请提供要查询的城市名称。"
    
    # 从 .env 读取您刚才填写的 32 位正确 Key
    api_key = os.getenv("QWEATHER_API_KEY")
    if not api_key:
        return "系统未配置和风天气 API Key，请在 .env 文件中添加 QWEATHER_API_KEY。"

    # 【关键修改】使用您的专属 API Host
    api_host = "np4nmu9nfj.re.qweatherapi.com"

    try:
        with httpx.Client(timeout=10.0) as client:
            
            # 【第一步】调用和风天气的城市搜索 API
            # URL 从 geoapi.qweather.com 换成了您的专属域名
            geo_url = f"https://{api_host}/geo/v2/city/lookup?location={city}&key={api_key}"
            geo_resp = client.get(geo_url)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            
            if geo_data.get("code") != "200" or not geo_data.get("location"):
                return f"抱歉，未能查找到城市“{city}”的信息，请确认城市名是否正确。"
                
            location_id = geo_data["location"][0]["id"]
            city_name = geo_data["location"][0]["name"]
            
            # 【第二步】使用获取到的 Location ID 获取实时天气
            # URL 从 devapi.qweather.com 换成了您的专属域名
            weather_url = f"https://{api_host}/v7/weather/now?location={location_id}&key={api_key}"
            weather_resp = client.get(weather_url)
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()
            
            if weather_data.get("code") == "200":
                now_weather = weather_data.get("now", {})
                temp = now_weather.get("temp", "未知")  # 温度
                text = now_weather.get("text", "未知")  # 天气状况
                wind_dir = now_weather.get("windDir", "未知") # 风向
                
                return f"实时获取成功：{city_name}当前的天气为{text}，气温{temp}摄氏度，{wind_dir}。请将这些信息以自然的方式告诉用户。"
            else:
                return f"抱歉，获取天气数据失败，和风天气 API 状态码：{weather_data.get('code')}。"

    except Exception as e:
        error_msg = str(e)
        print(f"[Weather Skill Error]: {error_msg}")
        return f"当前网络节点访问和风天气接口异常：{error_msg}。"