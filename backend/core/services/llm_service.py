"""
本地 Ollama 对话服务（真流式）：
- ChatOpenAI.stream 实时吐 token
- 角色系统提示词
- RAG 检索上下文注入
- 工具结果注入（天气/资讯）
"""

from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
from typing import Iterator, Optional, Dict, List
from urllib.parse import quote_plus
import os
import sys

import httpx
from django.conf import settings

TOKEN_MD_PATH = r"D:\Z-Desktop\找工作\8大模型开发\实战项目\Token记录\token.md"


# ================= 新增：动态引入外部 skill 目录 =================
# 获取项目根目录 (backend 的上一级)
PROJECT_ROOT = settings.BASE_DIR.parent

# 兼容你文件夹可能命名为 skill 或是 skills 的情况
SKILL_DIR = os.path.join(PROJECT_ROOT, 'skill')
if not os.path.exists(SKILL_DIR):
    SKILL_DIR = os.path.join(PROJECT_ROOT, 'skills')

# 拿到具体的子文件夹路径
WEATHER_DIR = os.path.join(SKILL_DIR, 'weather_skill')
NEWS_DIR = os.path.join(SKILL_DIR, 'news_skill')

# 将子文件夹直接加入系统路径，这样就不需要新建 __init__.py 文件了
for directory in [SKILL_DIR, WEATHER_DIR, NEWS_DIR]:
    if os.path.exists(directory) and directory not in sys.path:
        sys.path.append(directory)

# 尝试导入我们新写的独立 Skills
try:
    # 因为已经把具体的文件夹加入了路径，这里直接从文件名导入函数
    from weather_skill import get_realtime_weather
    from news_skill import get_realtime_news
    SKILLS_LOADED = True
except ImportError as e:
    print(f"警告：无法加载外部 Skill 模块：{e}")
    SKILLS_LOADED = False


try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from langchain_core.tools import tool

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None
    SystemMessage = HumanMessage = AIMessage = None

    def tool(func=None, **kwargs):
        if func is None:
            def decorator(f):
                return f
            return decorator
        return func


def _get_llm(streaming: bool = True):
    if not LANGCHAIN_AVAILABLE or not ChatOpenAI:
        return None
    return ChatOpenAI(
        model=getattr(settings, 'LLM_MODEL', 'qwen2.5:14b'),
        temperature=0.7,
        streaming=streaming,
        base_url=getattr(settings, 'OPENAI_BASE_URL', 'http://127.0.0.1:11434/v1'),
        api_key=getattr(settings, 'OPENAI_API_KEY', 'ollama'),
    )


# def build_system_prompt(character) -> str:
#     parts = [
#         character.system_prompt or '你是一个友善、共情、稳定的 AI 陪伴者。',
#         f'你的角色名是「{character.name}」，请始终保持该角色人设。',
#     ]
#     if getattr(character, 'opening_message', None):
#         parts.append(f'开场白参考：{character.opening_message}')
#     if isinstance(getattr(character, 'personality', None), list) and character.personality:
#         parts.append('性格标签：' + '、'.join(character.personality[:10]))
#     parts.append('回答要自然、简洁，不要重复句子。')
#     return '\n'.join(parts)
def build_system_prompt(character) -> str:
    # 动态获取当前时间
    now_str = datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S %A')
    
    parts = [
        f'【系统信息】：当前真实系统时间是 {now_str}。如果用户问“今天”、“现在”，请基于此时间回答。',
        character.system_prompt or '你是一个友善、共情、稳定的 AI 陪伴者。',
        f'你的角色名是「{character.name}」，请始终保持该角色人设。',
    ]
    if getattr(character, 'opening_message', None):
        parts.append(f'开场白参考：{character.opening_message}')
    if isinstance(getattr(character, 'personality', None), list) and character.personality:
        parts.append('性格标签：' + '、'.join(character.personality[:10]))
    parts.append('回答要自然、简洁，不要重复句子。如果查询了工具，请自然地把工具结果总结给用户。')
    return '\n'.join(parts)



@tool
def weather_tool(city: str) -> str:
    """查询城市天气。输入示例：北京"""
    city = (city or '').strip()
    if not city:
        return '天气工具：缺少城市名'
    timeout = float(getattr(settings, 'TOOL_HTTP_TIMEOUT', 8))
    url = f'https://wttr.in/{quote_plus(city)}?format=j1'
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        current = (data.get('current_condition') or [{}])[0]
        temp = current.get('temp_C', 'N/A')
        desc = ((current.get('weatherDesc') or [{}])[0] or {}).get('value', '')
        humidity = current.get('humidity', 'N/A')
        return f'{city}天气：{desc}，温度 {temp}°C，湿度 {humidity}%。'
    except Exception as exc:
        return f'天气工具失败：{exc}'


@tool
def news_tool(query: str) -> str:
    """搜索资讯新闻，输入示例：人工智能"""
    query = (query or '').strip()
    if not query:
        return '资讯工具：缺少关键词'
    timeout = float(getattr(settings, 'TOOL_HTTP_TIMEOUT', 8))
    rss_url = (
        'https://news.google.com/rss/search'
        f'?q={quote_plus(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans'
    )
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(rss_url)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        items = root.findall('.//item')[:5]
        if not items:
            return f'未检索到与「{query}」相关资讯。'
        lines = []
        for i, item in enumerate(items, start=1):
            title = re.sub(r'\s+', ' ', (item.findtext('title') or '').strip())
            link = (item.findtext('link') or '').strip()
            lines.append(f'{i}. {title}\n{link}')
        return '\n'.join(lines)
    except Exception as exc:
        return f'资讯工具失败：{exc}'


def build_chain(character, session_id: str, rag_retriever=None):
    """
    保留统一接口，供 views/consumers 复用。
    """
    llm = _get_llm(streaming=True)
    return {
        'type': 'stream_chat',
        'llm': llm,
        'system': build_system_prompt(character),
        'rag': rag_retriever,
    }


def _get_rag_context(rag_retriever, user_message: str) -> str:
    if not rag_retriever:
        return ''
    try:
        # LangChain retriever 新版推荐 invoke
        docs = rag_retriever.invoke(user_message) if hasattr(rag_retriever, 'invoke') else rag_retriever.get_relevant_documents(user_message)
        if not docs:
            return ''
        chunks = []
        for i, d in enumerate(docs[:4], start=1):
            chunks.append(f'[{i}] {getattr(d, "page_content", "")[:1200]}')
        return '\n'.join(chunks)
    except Exception:
        return ''

def _get_tool_context(user_message: str) -> str:
    msg = user_message.strip()
    if not msg:
        return ''

    tool_results: List[str] = []
    
    # 1. 触发天气 Skill
    if any(k in msg for k in ('天气', '温度', '下雨', '气温', '风力')):
        city_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,12})(的天气|天气|温度|下雨|气温)', msg)
        city = city_match.group(1) if city_match else ''
        for word in ['今天', '明天', '现在', '最近', '的', '你们']:
            city = city.replace(word, '')
        city = city.strip()
        if not city:
            city = '北京' # 默认城市
            
        if SKILLS_LOADED:
            # 调用真实的文件中的函数
            tool_results.append(get_realtime_weather(city))
        else:
            tool_results.append("系统错误：天气组件未加载。")

    # 2. 触发新闻 Skill
    if any(k in msg for k in ('新闻', '资讯', '热点', '最新消息', '热搜')):
        query = re.sub(r'(今天|明天|近期|的|新闻|资讯|热点|最新消息|告诉我|查一下|热搜)', '', msg).strip()
        if not query:
            query = '今日热点'
            
        if SKILLS_LOADED:
            # 调用真实的文件中的函数
            tool_results.append(get_realtime_news(query))
        else:
             tool_results.append("系统错误：新闻组件未加载。")

    return '\n\n'.join([r for r in tool_results if r])




# def stream_chat(
#     character,
#     session_id: str,
#     user_message: str,
#     chain_dict: Optional[Dict] = None,
#     rag_retriever=None,
#     history_messages: Optional[List[Dict[str, str]]] = None,
# ) -> Iterator[str]:
#     """
#     真流式输出：
#     - 直接调用 llm.stream(messages)
#     - 每个 token 立刻 yield
#     """
#     if not LANGCHAIN_AVAILABLE:
#         yield '（未安装 LangChain 依赖）'
#         return

#     if chain_dict is None:
#         chain_dict = build_chain(character, session_id, rag_retriever=rag_retriever)
#     llm = (chain_dict or {}).get('llm')
#     system_text = (chain_dict or {}).get('system') or build_system_prompt(character)
#     if not llm:
#         yield '（未能连接本地 Ollama，请检查 OPENAI_BASE_URL）'
#         return

#     rag_context = _get_rag_context(rag_retriever, user_message)
#     tool_context = _get_tool_context(user_message)

#     input_text = user_message
#     if rag_context:
#         input_text += f'\n\n【知识库检索结果】\n{rag_context}'
#     if tool_context:
#         input_text += f'\n\n【工具结果】\n{tool_context}'

#     messages = [SystemMessage(content=system_text)]
#     for h in (history_messages or []):
#         role = (h.get('role') or '').strip()
#         content = h.get('content') or ''
#         if not content:
#             continue
#         if role == 'user':
#             messages.append(HumanMessage(content=content))
#         elif role == 'assistant':
#             messages.append(AIMessage(content=content))
#     messages.append(HumanMessage(content=input_text))

#     try:
#         for chunk in llm.stream(messages):
#             token = getattr(chunk, 'content', '') or ''
#             if token:
#                 yield token
#     except Exception as exc:
#         yield f'（流式回复失败：{exc}）'

def stream_chat(
    character,
    session_id: str,
    user_message: str,
    chain_dict: Optional[Dict] = None,
    rag_retriever=None,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> Iterator[str]:
    """
    真流式输出：
    - 直接调用 llm.stream(messages)
    - 每个 token 立刻 yield
    - 【新增】在流式结束后捕获或估算 Token，并记录到公共 Markdown 文件中
    """
    if not LANGCHAIN_AVAILABLE:
        yield '（未安装 LangChain 依赖）'
        return

    if chain_dict is None:
        chain_dict = build_chain(character, session_id, rag_retriever=rag_retriever)
    llm = (chain_dict or {}).get('llm')
    system_text = (chain_dict or {}).get('system') or build_system_prompt(character)
    if not llm:
        yield '（未能连接本地 Ollama，请检查 OPENAI_BASE_URL）'
        return

    rag_context = _get_rag_context(rag_retriever, user_message)
    tool_context = _get_tool_context(user_message)

    input_text = user_message
    if rag_context:
        input_text += f'\n\n【知识库检索结果】\n{rag_context}'
    if tool_context:
        input_text += f'\n\n【工具结果】\n{tool_context}'

    messages = [SystemMessage(content=system_text)]
    for h in (history_messages or []):
        role = (h.get('role') or '').strip()
        content = h.get('content') or ''
        if not content:
            continue
        if role == 'user':
            messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=input_text))

    # ====== 准备记录 Token 的变量 ======
    full_response = ""
    prompt_tokens = 0
    comp_tokens = 0
    project_name = "agent_voice" # 当前项目名，如果以后复制到别的项目，改这个字符串即可
    model_name = getattr(settings, 'LLM_MODEL', 'qwen2.5:14b')
    # ==================================

    try:
        for chunk in llm.stream(messages):
            token = getattr(chunk, 'content', '') or ''
            if token:
                full_response += token
                yield token
            
            # 尝试从 LangChain 较新版本中直接获取流式返回的 metadata
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                prompt_tokens = chunk.usage_metadata.get('input_tokens', 0)
                comp_tokens = chunk.usage_metadata.get('output_tokens', 0)
                
    except Exception as exc:
        yield f'（流式回复失败：{exc}）'
        
    finally:
        # 如果 Ollama 或老版本 LangChain 没有返回官方统计，我们使用 tiktoken 估算
        if prompt_tokens == 0 and comp_tokens == 0 and full_response:
            try:
                import tiktoken
                enc = tiktoken.get_encoding("cl100k_base")
                # 拼接所有输入内容进行估算
                prompt_str = "\n".join([m.content for m in messages if hasattr(m, 'content') and m.content])
                prompt_tokens = len(enc.encode(prompt_str))
                comp_tokens = len(enc.encode(full_response))
            except ImportError:
                print("未安装 tiktoken，无法估算 Token（请运行 pip install tiktoken）")
        
        # 将结果写入全局 markdown 文件
        if prompt_tokens > 0 or comp_tokens > 0:
            try:
                log_token_usage(project_name, model_name, prompt_tokens, comp_tokens)
            except Exception as e:
                print(f"调用 Token 日志记录失败: {e}")





# 记录本地大模型token消耗情况
def log_token_usage(project_name: str, model_name: str, prompt_tokens: int, completion_tokens: int):
    """
    更新公共的 token.md 文件，追加新记录并自动汇总统计信息
    """
    total_tokens = prompt_tokens + completion_tokens
    if total_tokens == 0:
        return

    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 确保文件夹存在
    os.makedirs(os.path.dirname(TOKEN_MD_PATH), exist_ok=True)

    lines = []
    if os.path.exists(TOKEN_MD_PATH):
        with open(TOKEN_MD_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    # 1. 提取历史日志数据
    logs = []
    in_log_section = False
    for line in lines:
        if line.startswith("| 时间"):
            in_log_section = True
            continue
        if line.startswith("|---"):
            continue
        if in_log_section and line.startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 6:
                try:
                    logs.append({
                        "time": parts[0],
                        "project": parts[1],
                        "model": parts[2],
                        "prompt": int(parts[3]),
                        "completion": int(parts[4]),
                        "total": int(parts[5])
                    })
                except ValueError:
                    pass # 忽略解析错误的行

    # 2. 加上本次的新记录
    logs.append({
        "time": now_str,
        "project": project_name,
        "model": model_name,
        "prompt": prompt_tokens,
        "completion": completion_tokens,
        "total": total_tokens
    })

    # 3. 重新计算各种维度的统计信息
    global_total = sum(log["total"] for log in logs)
    
    project_stats = {}
    model_stats = {}
    for log in logs:
        p = log["project"]
        m = log["model"]
        project_stats[p] = project_stats.get(p, 0) + log["total"]
        model_stats[m] = model_stats.get(m, 0) + log["total"]

    # 4. 重写 Markdown 文件，生成清晰的面板和日志
    try:
        with open(TOKEN_MD_PATH, 'w', encoding='utf-8') as f:
            f.write("# 🤖 全局大模型 Token 消耗记录\n\n")
            
            f.write("## 📊 汇总数据\n")
            f.write(f"- **全局总消耗**: `{global_total}` Tokens\n\n")
            
            f.write("### 📁 按项目统计\n")
            for p, t in project_stats.items():
                f.write(f"- **{p}**: `{t}` Tokens\n")
            f.write("\n")
            
            f.write("### 🧠 按模型统计\n")
            for m, t in model_stats.items():
                f.write(f"- **{m}**: `{t}` Tokens\n")
            f.write("\n")
            
            f.write("## 📝 详细日志\n")
            f.write("| 时间 | 项目名称 | 模型名称 | 输入 Tokens | 输出 Tokens | 总 Tokens |\n")
            f.write("|---|---|---|---|---|---|\n")
            # 倒序输出，让最新的记录在最上面
            for log in reversed(logs):
                f.write(f"| {log['time']} | {log['project']} | {log['model']} | {log['prompt']} | {log['completion']} | {log['total']} |\n")
    except Exception as e:
        print(f"写入 token.md 失败: {e}")
# =================================================================