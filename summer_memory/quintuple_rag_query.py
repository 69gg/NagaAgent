import requests
import json
import logging
import sys
import os
import re
import time
from typing import List, Dict, Any

# 添加项目根目录到路径，以便导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import config
from openai import OpenAI
from .json_utils import clean_and_parse_json

# 初始化OpenAI客户端
client = OpenAI(
    api_key=config.api.api_key,
    base_url=config.api.base_url
)

API_URL = f"{config.api.base_url.rstrip('/')}/chat/completions"

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 缓存最近处理的文本
recent_context = []

# 定义关键词响应的Pydantic模型
from pydantic import BaseModel
class KeywordResponse(BaseModel):
    keywords: List[str]

def set_context(texts):
    """设置查询上下文"""
    global recent_context
    # 使用配置中的上下文长度，默认为5
    context_length = getattr(config.grag, 'context_length', 5)
    recent_context = texts[:context_length]  # 限制上下文长度
    logger.info(f"更新查询上下文: {len(recent_context)} 条记录")

def _extract_keywords_structured(user_question: str, context_str: str) -> List[str]:
    """使用结构化输出提取关键词"""
    system_prompt = """
你是一个专业的中文文本关键词提取专家。你的任务是从给定的上下文和用户问题中提取与知识图谱相关的关键词。

关键词类型包括但不限于：
- 人物（如：小明、张三、李四）
- 物体（如：足球、电脑、手机）
- 关系（如：踢、拥有、创建）
- 实体类型（如：人物、地点、组织、物品）
- 概念（如：学习、工作、生活）

请仔细分析文本，提取所有与知识图谱相关的核心关键词，避免无关词。
"""

    max_retries = 1  # 减少重试次数，失败后立即回退

    for attempt in range(max_retries + 1):
        logger.info(f"尝试使用结构化输出提取关键词 (第{attempt + 1}次)")

        try:
            # 尝试使用结构化输出
            completion = client.beta.chat.completions.parse(
                model=config.api.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"基于以下上下文和用户问题，提取与知识图谱相关的关键词：\n\n上下文：\n{context_str}\n\n问题：{user_question}"}
                ],
                response_format=KeywordResponse,
                max_tokens=config.api.max_tokens,
                temperature=0.3,
                timeout=600
            )

            # 解析结果
            result = completion.choices[0].message.parsed
            keywords = result.keywords
            
            logger.info(f"结构化输出成功，提取到 {len(keywords)} 个关键词")
            return keywords

        except Exception as e:
            logger.warning(f"结构化输出失败: {str(e)}")
            # 立即回退到传统方法，不再重试
            break
    
    logger.info("结构化输出失败，立即回退到传统JSON解析方法")
    return _extract_keywords_fallback(user_question, context_str)

def _extract_keywords_fallback(user_question: str, context_str: str) -> List[str]:
    """传统JSON解析的关键词提取（回退方案）"""
    prompt = f"""
基于以下上下文和用户问题，提取与知识图谱相关的关键词（如人物、物体、关系、实体类型），
仅返回核心关键词，避免无关词。直接返回关键词数组的JSON格式：

上下文：
{context_str}

问题：{user_question}

输出格式：[["关键词1", "关键词2", "关键词3"]]
"""

    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.api.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.api.max_tokens,
                temperature=0.3,
                timeout=600
            )

            content = response.choices[0].message.content.strip()
            
            # 使用统一的JSON清理和解析工具
            keywords = clean_and_parse_json(content, expected_type=list, default=[])
            
            if keywords:
                logger.info(f"传统方法成功，提取到 {len(keywords)} 个关键词")
                return keywords
            else:
                logger.warning("传统方法JSON解析失败，尝试额外解析策略")
                # 尝试直接提取数组作为最后的策略
                if '[' in content and ']' in content:
                    try:
                        start = content.index('[')
                        end = content.rindex(']') + 1
                        array_content = content[start:end]
                        keywords = json.loads(array_content)
                        if isinstance(keywords, list):
                            logger.info(f"数组提取策略成功，提取到 {len(keywords)} 个关键词")
                            return keywords
                    except:
                        pass

        except Exception as e:
            logger.error(f"传统方法提取失败: {str(e)}")
            if attempt < max_retries:
                time.sleep(1 + attempt)

    return []

def query_knowledge_with_keywords(user_question, predefined_keywords=None, memory_types=None):
    """使用预提取关键词查询知识图谱，支持记忆类型过滤"""
    context_str = "\n".join(recent_context) if recent_context else "无上下文"
    
    # 使用预定义的关键词或提取关键词
    if predefined_keywords:
        keywords = predefined_keywords
        logger.info(f"使用预定义关键词: {keywords}")
    else:
        # 首先尝试使用结构化输出
        keywords = _extract_keywords_structured(user_question, context_str)
        logger.info(f"提取关键词: {keywords}")
    
    # 如果没有关键词，返回空字符串而不是错误信息
    if not keywords:
        logger.warning("未提取到关键词")
        return ""
    
    # 验证关键词格式
    if not isinstance(keywords, list):
        logger.error(f"关键词格式错误: {keywords}")
        return ""
    
    try:
        from .quintuple_graph import query_graph_by_keywords
        quintuples = query_graph_by_keywords(keywords, memory_types)
        if not quintuples:
            logger.info(f"未找到相关五元组: {keywords}")
            return ""

        answer = "我在知识图谱中找到以下相关信息：\n\n"
        for quintuple in quintuples:
            if isinstance(quintuple, dict):
                # 新格式：包含时间信息的增强五元组
                h = quintuple["subject"]
                h_type = quintuple["subject_type"]
                r = quintuple["predicate"]
                t = quintuple["object"]
                t_type = quintuple["object_type"]
                
                # 获取时间信息
                timestamp = quintuple.get("timestamp")
                memory_type = quintuple.get("memory_type", "fact")
                importance_score = quintuple.get("importance_score", 0.5)
                
                # 格式化时间
                time_str = ""
                if timestamp:
                    import time
                    time_str = f" (时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))})"
                
                # 构建带时间信息的回答
                answer += f"- {h}({h_type}) —[{r}]→ {t}({t_type}){time_str}\n"
                answer += f"  记忆类型: {memory_type}, 重要性: {importance_score:.2f}\n"
            else:
                # 旧格式：兼容性处理
                h, h_type, r, t, t_type = quintuple
                answer += f"- {h}({h_type}) —[{r}]→ {t}({t_type})\n"
        return answer

    except Exception as e:
        logger.error(f"查询知识图谱过程中发生错误: {e}")
        return ""


def query_knowledge(user_question):
    """使用配置的模型API提取关键词并查询知识图谱（保持向后兼容）"""
    context_str = "\n".join(recent_context) if recent_context else "无上下文"
    
    # 首先尝试使用结构化输出
    keywords = _extract_keywords_structured(user_question, context_str)
    
    # 如果结构化输出失败，返回空字符串
    if not keywords:
        logger.warning("所有提取方法都失败，未提取到关键词")
        return ""

    # 验证关键词格式
    if not isinstance(keywords, list):
        logger.error(f"关键词格式错误: {keywords}")
        return ""

    if not keywords:
        logger.warning("未提取到关键词")
        return ""

    logger.info(f"提取关键词: {keywords}")
    
    try:
        from .quintuple_graph import query_graph_by_keywords
        quintuples = query_graph_by_keywords(keywords)
        if not quintuples:
            logger.info(f"未找到相关五元组: {keywords}")
            return ""

        answer = "我在知识图谱中找到以下相关信息：\n\n"
        for quintuple in quintuples:
            if isinstance(quintuple, dict):
                # 新格式：包含时间信息的增强五元组
                h = quintuple["subject"]
                h_type = quintuple["subject_type"]
                r = quintuple["predicate"]
                t = quintuple["object"]
                t_type = quintuple["object_type"]
                
                # 获取时间信息
                timestamp = quintuple.get("timestamp")
                memory_type = quintuple.get("memory_type", "fact")
                importance_score = quintuple.get("importance_score", 0.5)
                
                # 格式化时间
                time_str = ""
                if timestamp:
                    import time
                    time_str = f" (时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))})"
                
                # 构建带时间信息的回答
                answer += f"- {h}({h_type}) —[{r}]→ {t}({t_type}){time_str}\n"
                answer += f"  记忆类型: {memory_type}, 重要性: {importance_score:.2f}\n"
            else:
                # 旧格式：兼容性处理
                h, h_type, r, t, t_type = quintuple
                answer += f"- {h}({h_type}) —[{r}]→ {t}({t_type})\n"
        return answer

    except Exception as e:
        logger.error(f"查询知识图谱过程中发生错误: {e}")
        return ""
