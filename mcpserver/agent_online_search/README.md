# 联网搜索Agent

调用searxng搜索API，返回相关实时信息。

## 功能特性

- 调用博查搜索API进行网页搜索
- 返回格式化的搜索结果供AI参考
- 支持自定义搜索结果数量
- 多种配置方式（环境变量、配置文件等）

## 依赖

请查看 [requirements.txt](requirements.txt) 文件了解详细依赖。

## 配置说明

### 1. 获取API密钥

1. 访问博查AI官网注册账号
2. 获取API密钥

### 2. 配置方式

博查搜索Agent支持多种配置方式，按优先级从高到低：

#### 方式一：环境变量
```bash
export BOCHA_API_KEY="your-bocha-api-key-here"
```

#### 方式二：config.json配置文件
在项目根目录的`config.json`文件中添加以下配置：
```json
{
  "online_search": {
    "Bocha_API_KEY": "your-bocha-api-key-here",
    "Bocha_Url": "https://api.bochaai.com/v1/web-search",
    "Bocha_count": 5
  }
}
```

#### 方式三：默认配置
如果以上配置都未设置，Agent将使用默认配置：
- API密钥：`your-bocha-api-key-here`
- API URL：`https://api.bochaai.com/v1/web-search`
- 搜索结果数量：5

## 使用方法

### 工具调用格式

```json
{
  "agentType": "mcp",
  "service_name": "BochaSearchAgent",
  "tool_name": "search",
  "query": "搜索内容"
}
```

### 调用示例

```json
{
  "agentType": "mcp",
  "service_name": "BochaSearchAgent",
  "tool_name": "search",
  "query": "天空为什么是蓝色的？"
}
```

### 参数说明

- `query` (必需): 搜索内容

## 返回格式

```json
{
  "status": "ok",
  "message": "搜索完成",
  "data": "格式化的搜索结果",
  "raw_data": [
    {
      "title": "文章标题",
      "url": "文章链接",
      "snippet": "文章摘要",
      "summary": "文章总结"
    }
  ]
}
```

## 错误处理

当搜索失败时，会返回以下格式的错误信息：

```json
{
  "status": "error",
  "message": "错误描述",
  "data": {}
}
```

## 开发指南

### 本地测试

1. 确保已安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置API密钥（任选一种方式）：
   - 设置环境变量
   - 修改config.json文件

3. 在NagaAgent中调用搜索功能

## 注意事项

1. 请妥善保管您的API密钥，不要泄露给他人
2. 遵守博查API的使用条款和限制
3. 搜索结果的数量可以通过配置中的`count`参数调整
4. 如果遇到网络问题，请检查网络连接和API服务状态

## 异常码

| http异常码 | 消息体                                                       | 异常原因                                | 处理方式                                                     |
| ---------- | ------------------------------------------------------------ | --------------------------------------- | ------------------------------------------------------------ |
| 403        | {  "code": "403",  "message": "You do not have enough money",  "log_id": "c66aac17eab1bb7e"} | 余额不足                                | 请前往 https://open.bochaai.com 进行充值                     |
| 400        | {  "code": "400",  "message": "Missing parameter query",  "log_id": "c66aac17eab1bb7e"} | 请求参数缺失                            |                                                              |
| 400        | {  "code": "400",  "message": "The API KEY is missing",  "log_id": "c66aac17eab1bb7e"} | 权限校验失败，Header 缺少 Authorization |                                                              |
| 401        | {  "code": "401",  "message": "Invalid API KEY",  "log_id": "c66aac17eab1bb7e"} | API KEY无效                             | 权限校验失败                                                 |
| 429        | {  "code": "429",  "message": "You have reached the request limit",  "log_id": "c66aac17eab1bb7e"} | 请求频达到率限制                        | 频率限制与总充值金额有关，具体详见：[API 定价](https://aq6ky2b8nql.feishu.cn/wiki/JYSbwzdPIiFnz4kDYPXcHSDrnZb) |
| 500        | {  "code": "500",  "message": "xxxx",  "log_id": "c66aac17eab1bb7e"} | 各种异常                                |                                                              |