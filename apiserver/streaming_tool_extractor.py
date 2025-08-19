#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式工具调用提取器
实时检测和提取AI输出中的工具调用，支持中英文括号
"""

import re
import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any
from .tool_call_utils import parse_tool_calls, execute_tool_calls

logger = logging.getLogger("StreamingToolExtractor")

class StreamingToolCallExtractor:
    """流式工具调用提取器"""
    
    def __init__(self, mcp_manager=None):
        self.tool_call_buffer = ""  # 工具调用缓冲区
        self.is_in_tool_call = False  # 是否在工具调用中
        self.brace_count = 0  # 括号计数
        self.mcp_manager = mcp_manager
        self.text_buffer = ""  # 普通文本缓冲区
        self.sentence_endings = r"[。？！；\.\?\!\;]"  # 断句标点
        
        # 回调函数
        self.on_text_chunk = None  # 文本块回调
        self.on_sentence = None    # 句子回调
        self.on_tool_call = None   # 工具调用回调
        self.on_tool_result = None # 工具结果回调
        
        # 语音集成（可选）
        self.voice_integration = None
        
    def set_callbacks(self, 
                     on_text_chunk: Optional[Callable] = None,
                     on_sentence: Optional[Callable] = None,
                     on_tool_call: Optional[Callable] = None,
                     on_tool_result: Optional[Callable] = None,
                     voice_integration=None):
        """设置回调函数"""
        self.on_text_chunk = on_text_chunk
        self.on_sentence = on_sentence
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.voice_integration = voice_integration
    
    async def process_text_chunk(self, text_chunk: str):
        """处理文本块，分离普通文本和工具调用"""
        if not text_chunk:
            return None
            
        results = []
        
        for char in text_chunk:
            if char in '{｛':  # 检测到开始括号
                if not self.is_in_tool_call:
                    # 开始工具调用，先处理累积的普通文本
                    if self.text_buffer:
                        result = await self._flush_text_buffer()
                        if result:
                            results.append(result)
                    
                    self.is_in_tool_call = True
                    self.tool_call_buffer = char
                    self.brace_count = 1
                else:
                    # 嵌套括号
                    self.tool_call_buffer += char
                    self.brace_count += 1
                    
            elif char in '}｝':  # 检测到结束括号
                if self.is_in_tool_call:
                    self.tool_call_buffer += char
                    self.brace_count -= 1
                    
                    if self.brace_count == 0:  # 工具调用结束
                        # 提取完整的工具调用
                        tool_call = self.tool_call_buffer
                        self.tool_call_buffer = ""
                        self.is_in_tool_call = False
                        
                        # 处理工具调用
                        result = await self._process_tool_call(tool_call)
                        if result:
                            results.append(result)
                        
            else:  # 普通字符
                if self.is_in_tool_call:
                    self.tool_call_buffer += char
                else:
                    # 普通文本，累积到缓冲区
                    self.text_buffer += char
                    
                    # 检查是否形成完整句子
                    if re.search(self.sentence_endings, char):
                        # 提取完整句子
                        sentences = re.split(self.sentence_endings, self.text_buffer)
                        if len(sentences) > 1:
                            complete_sentence = sentences[0] + char  # 包含标点
                            if complete_sentence.strip():
                                # 发送文本块回调（用于前端显示）
                                if self.on_text_chunk:
                                    try:
                                        # 尝试异步调用
                                        if asyncio.iscoroutinefunction(self.on_text_chunk):
                                            result = await self.on_text_chunk(complete_sentence, "chunk")
                                        else:
                                            # 同步调用
                                            result = self.on_text_chunk(complete_sentence, "chunk")
                                        
                                        if result:
                                            results.append(result)
                                    except Exception as e:
                                        logger.error(f"文本块回调错误: {e}")
                                
                                # 发送句子回调（用于其他处理）
                                if self.on_sentence:
                                    try:
                                        # 尝试异步调用
                                        if asyncio.iscoroutinefunction(self.on_sentence):
                                            await self.on_sentence(complete_sentence, "sentence")
                                        else:
                                            # 同步调用
                                            self.on_sentence(complete_sentence, "sentence")
                                    except Exception as e:
                                        logger.error(f"句子回调错误: {e}")
                                
                                # 发送到语音集成（普通文本，非工具调用）
                                if self.voice_integration:
                                    try:
                                        import threading
                                        threading.Thread(
                                            target=self.voice_integration.receive_text_chunk,
                                            args=(complete_sentence,),
                                            daemon=True
                                        ).start()
                                    except Exception as e:
                                        logger.error(f"语音集成错误: {e}")
                            
                            # 更新缓冲区，过滤空字符串
                            remaining_sentences = [s for s in sentences[1:] if s.strip()]
                            self.text_buffer = "".join(remaining_sentences)
        
        # 返回所有结果
        return results
    
    async def _flush_text_buffer(self):
        """刷新文本缓冲区"""
        if self.text_buffer:
            # 发送文本块
            if self.on_text_chunk:
                try:
                    # 尝试异步调用
                    if asyncio.iscoroutinefunction(self.on_text_chunk):
                        result = await self.on_text_chunk(self.text_buffer, "chunk")
                    else:
                        # 同步调用
                        result = self.on_text_chunk(self.text_buffer, "chunk")
                    
                    if result:
                        # 返回数据给调用者
                        return result
                except Exception as e:
                    logger.error(f"文本块回调错误: {e}")
            
            # 发送到语音集成（普通文本，非工具调用）
            if self.voice_integration:
                try:
                    import threading
                    threading.Thread(
                        target=self.voice_integration.receive_text_chunk,
                        args=(self.text_buffer,),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.error(f"语音集成错误: {e}")
            
            self.text_buffer = ""
        return None
    

    
    async def _process_tool_call(self, tool_call_text: str):
        """处理工具调用"""
        try:
            logger.info(f"检测到工具调用: {tool_call_text[:100]}...")
            
            # 发送工具调用回调
            if self.on_tool_call:
                try:
                    # 尝试异步调用
                    if asyncio.iscoroutinefunction(self.on_tool_call):
                        result = await self.on_tool_call(tool_call_text, "tool_call")
                    else:
                        # 同步调用
                        result = self.on_tool_call(tool_call_text, "tool_call")
                    
                    if result:
                        return result
                except Exception as e:
                    logger.error(f"工具调用回调错误: {e}")
            
            # 解析JSON
            tool_calls = parse_tool_calls(tool_call_text)
            
            if tool_calls:
                logger.info(f"解析到 {len(tool_calls)} 个工具调用")
                
                # 执行工具调用
                if self.mcp_manager:
                    results = await execute_tool_calls(tool_calls, self.mcp_manager)
                    
                    # 发送工具结果回调
                    if self.on_tool_result:
                        try:
                            # 尝试异步调用
                            if asyncio.iscoroutinefunction(self.on_tool_result):
                                result = await self.on_tool_result(results, "tool_result")
                            else:
                                # 同步调用
                                result = self.on_tool_result(results, "tool_result")
                            
                            if result:
                                return result
                        except Exception as e:
                            logger.error(f"工具结果回调错误: {e}")
                    
                    logger.info(f"工具调用执行完成: {results[:100]}...")
                else:
                    logger.warning("MCP管理器未设置，跳过工具调用执行")
            else:
                logger.warning("工具调用解析失败")
                
        except Exception as e:
            error_msg = f"工具调用处理失败: {str(e)}"
            logger.error(error_msg)
            
            # 发送错误回调
            if self.on_tool_result:
                try:
                    # 尝试异步调用
                    if asyncio.iscoroutinefunction(self.on_tool_result):
                        result = await self.on_tool_result(error_msg, "tool_error")
                    else:
                        # 同步调用
                        result = self.on_tool_result(error_msg, "tool_error")
                    
                    if result:
                        return result
                except Exception as e:
                    logger.error(f"工具错误回调错误: {e}")
        
        return None
    
    async def finish_processing(self):
        """完成处理，清理剩余内容"""
        results = []
        
        # 处理剩余的文本
        if self.text_buffer:
            result = await self._flush_text_buffer()
            if result:
                results.append(result)
        
        # 处理未完成的工具调用
        if self.is_in_tool_call and self.tool_call_buffer:
            logger.warning(f"检测到未完成的工具调用: {self.tool_call_buffer}")
            # 可以选择丢弃或特殊处理
        
        return results if results else None
    
    def reset(self):
        """重置提取器状态"""
        self.tool_call_buffer = ""
        self.is_in_tool_call = False
        self.brace_count = 0
        self.text_buffer = ""

class StreamingResponseProcessor:
    """流式响应处理器 - 集成工具调用提取和文本处理"""
    
    def __init__(self, mcp_manager=None):
        self.tool_extractor = StreamingToolCallExtractor(mcp_manager)
        self.response_buffer = ""
        self.is_processing = False
        
    async def process_ai_response(self, response_stream, callbacks: Dict[str, Callable]):
        """处理AI流式响应"""
        self.is_processing = True
        self.response_buffer = ""
        
        # 设置回调函数
        self.tool_extractor.set_callbacks(**callbacks)
        
        try:
            async for chunk in response_stream:
                if not self.is_processing:
                    break
                    
                chunk_text = str(chunk)
                self.response_buffer += chunk_text
                
                # 使用工具调用提取器处理
                await self.tool_extractor.process_text_chunk(chunk_text)
                
        except Exception as e:
            logger.error(f"AI流式响应处理错误: {e}")
        finally:
            self.is_processing = False
            # 完成处理
            await self.tool_extractor.finish_processing()
    
    def stop_processing(self):
        """停止处理"""
        self.is_processing = False
    
    def get_response_buffer(self) -> str:
        """获取响应缓冲区内容"""
        return self.response_buffer
