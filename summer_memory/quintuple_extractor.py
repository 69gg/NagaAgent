import json
import logging
import re
import sys
import os
import time
import asyncio
import requests

# 添加项目根目录到路径，以便导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def extract_quintuples_async(text):
    """异步版本的五元组提取"""
    prompt = f"""从以下文本中提取五元组关系，返回JSON格式数组。

格式：[["主语", "主语类型", "谓语", "宾语", "宾语类型"]]

示例：
文本：小明在公园踢足球
结果：[["小明", "人物", "踢", "足球", "物品"], ["小明", "人物", "在", "公园", "地点"]]

文本：{text}
结果："""

    # 创建AsyncOpenAI客户端
    client = AsyncOpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
    
    # 重试机制配置
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"尝试提取五元组 (第{attempt + 1}次)")
            
            logger.debug(f"使用模型: {config.api.model}")
            logger.debug(f"Prompt长度: {len(prompt)}")
            
            response = await client.chat.completions.create(
                model=config.api.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,  # 增加token限制
                temperature=0.3,  # 降低温度，更确定性输出
                timeout=600 + (attempt * 5)   # 对于推理模型
            )
            
            logger.debug(f"API响应成功")
            logger.debug(f"完整响应对象: {response}")
            logger.debug(f"响应choices数量: {len(response.choices)}")
            
            if not response.choices or len(response.choices) == 0:
                logger.error("API响应中没有choices")
                return []
            
            choice = response.choices[0]
            logger.debug(f"Choice对象: {choice}")
            
            if not hasattr(choice, 'message') or not choice.message:
                logger.error("Choice中没有message")
                return []
            
            content = choice.message.content
            logger.debug(f"API响应内容: {repr(content)}")
            logger.debug(f"内容类型: {type(content)}")
            logger.debug(f"内容长度: {len(content) if content else 0}")
            
            if not content or not content.strip():
                logger.error("API返回内容为空")
                # 记录完整的响应用于调试
                logger.error(f"完整API响应: {response}")
                return []
            
            # 尝试提取JSON
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                json_str = match.group(1)
                logger.debug(f"从代码块提取JSON: {json_str}")
            else:
                json_str = content.strip()
                logger.debug(f"直接使用内容作为JSON: {json_str}")

            # 验证JSON格式
            try:
                quintuples = json.loads(json_str)
                logger.info(f"JSON解析成功: {quintuples}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"尝试解析的JSON字符串: {json_str}")
                return []
            
            # 验证五元组格式
            if not isinstance(quintuples, list):
                logger.error(f"API返回的不是数组: {type(quintuples)}")
                return []
            
            valid_quintuples = []
            for i, item in enumerate(quintuples):
                if isinstance(item, list) and len(item) == 5:
                    valid_quintuples.append(tuple(item))
                else:
                    logger.warning(f"跳过无效的五元组 {i}: {item}")
            
            logger.info(f"提取到 {len(valid_quintuples)} 个有效五元组")
            return valid_quintuples

        except Exception as e:
            logger.error(f"调用API抽取五元组失败 (第{attempt + 1}次): {e}")
            if attempt < max_retries:
                await asyncio.sleep(1)  # 重试前等待1秒
                continue
            else:
                return []
    
    return []


def extract_quintuples(text):
    """同步版本的五元组提取"""
    prompt = f"""从以下文本中提取五元组关系，返回JSON格式数组。

格式：[["主语", "主语类型", "谓语", "宾语", "宾语类型"]]

示例：
文本：小明在公园踢足球
结果：[["小明", "人物", "踢", "足球", "物品"], ["小明", "人物", "在", "公园", "地点"]]

文本：{text}
结果："""

    from openai import OpenAI
    
    # 创建OpenAI客户端
    client = OpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
    
    # 重试机制配置
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"尝试提取五元组 (第{attempt + 1}次)")
            
            logger.debug(f"使用模型: {config.api.model}")
            logger.debug(f"Prompt长度: {len(prompt)}")
            
            response = client.chat.completions.create(
                model=config.api.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,  # 增加token限制
                temperature=0.3,  # 降低温度，更确定性输出
                timeout=600 + (attempt * 5)   # 对于推理模型
            )
            
            logger.debug(f"API响应成功")
            logger.debug(f"完整响应对象: {response}")
            logger.debug(f"响应choices数量: {len(response.choices)}")
            
            if not response.choices or len(response.choices) == 0:
                logger.error("API响应中没有choices")
                return []
            
            choice = response.choices[0]
            logger.debug(f"Choice对象: {choice}")
            
            if not hasattr(choice, 'message') or not choice.message:
                logger.error("Choice中没有message")
                return []
            
            content = choice.message.content
            logger.debug(f"API响应内容: {repr(content)}")
            logger.debug(f"内容类型: {type(content)}")
            logger.debug(f"内容长度: {len(content) if content else 0}")
            
            if not content or not content.strip():
                logger.error("API返回内容为空")
                # 记录完整的响应用于调试
                logger.error(f"完整API响应: {response}")
                return []
            
            # 尝试提取JSON
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                json_str = match.group(1)
                logger.debug(f"从代码块提取JSON: {json_str}")
            else:
                json_str = content.strip()
                logger.debug(f"直接使用内容作为JSON: {json_str}")

            # 验证JSON格式
            try:
                quintuples = json.loads(json_str)
                logger.info(f"JSON解析成功: {quintuples}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"尝试解析的JSON字符串: {json_str}")
                return []
            
            # 验证五元组格式
            if not isinstance(quintuples, list):
                logger.error(f"API返回的不是数组: {type(quintuples)}")
                return []
            
            valid_quintuples = []
            for i, item in enumerate(quintuples):
                if isinstance(item, list) and len(item) == 5:
                    valid_quintuples.append(tuple(item))
                else:
                    logger.warning(f"跳过无效的五元组 {i}: {item}")
            
            logger.info(f"提取到 {len(valid_quintuples)} 个有效五元组")
            return valid_quintuples

        except Exception as e:
            logger.error(f"调用API抽取五元组失败 (第{attempt + 1}次): {e}")
            if attempt < max_retries:
                time.sleep(1)  # 重试前等待1秒
                continue
            else:
                return []
    
    return []