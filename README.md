# upload_post_mcp

基于 Python `mcp` 库实现的 MCP Server，用于封装 `upload-post.com` API。

提供两个 MCP 工具：

- `publish_video_to_tiktok`
- `check_upload_status`

`API Key` 从环境变量 `UPLOADPOST_API_KEY` 读取。

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

至少需要配置：

```bash
UPLOADPOST_API_KEY=your_api_key
```

可选配置（用于适配你的 Upload-Post 实际接口路径）：

```bash
UPLOADPOST_BASE_URL=https://upload-post.com/api
UPLOADPOST_PUBLISH_TIKTOK_PATH=/v1/publish/tiktok
UPLOADPOST_CHECK_STATUS_PATH_TEMPLATE=/v1/uploads/{upload_id}/status
UPLOADPOST_TIMEOUT=30
```

## 3. 启动 MCP Server

```bash
python server.py
```

## 4. 工具说明

### `publish_video_to_tiktok`

参数：

- `video_url: str` 必填，公开视频 URL
- `caption: str | None` 可选
- `scheduled_at: str | None` 可选，ISO8601 时间
- `hashtags: list[str] | None` 可选
- `additional_params: dict[str, Any] | None` 可选，透传额外字段

### `check_upload_status`

参数：

- `upload_id: str` 必填

说明：若 Upload-Post 官方路径与你当前默认值不同，修改环境变量中的路径即可，无需改代码。