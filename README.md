# upload_post_mcp

基于 Python `mcp` 库实现的 MCP Server，用于封装 `upload-post.com` API。

提供以下 MCP 工具：

- `publish_video_to_tiktok`
- `check_upload_status`
- `list_connected_accounts`
- `publish_local_video_to_tiktok`

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
UPLOADPOST_BASE_URL=https://api.upload-post.com/api
UPLOADPOST_PUBLISH_TIKTOK_PATH=/v1/publish/tiktok
UPLOADPOST_CHECK_STATUS_PATH_TEMPLATE=/v1/uploads/{upload_id}/status
UPLOADPOST_CONNECTED_ACCOUNTS_PATH=/uploadposts/users
UPLOADPOST_UPLOAD_ASSET_PATH=/upload
UPLOADPOST_UPLOAD_FILE_FIELD=video
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

### `list_connected_accounts`

参数：

- 无

### `publish_local_video_to_tiktok`

功能：自动完成两步操作，不需要手动准备 URL。

1. 使用 `multipart/form-data` 上传本地视频文件
2. 自动提取上传后的 URL 并调用 TikTok 发布接口

参数：

- `local_file_path: str` 必填，本地视频文件路径
- `caption: str | None` 可选
- `scheduled_at: str | None` 可选，ISO8601 时间
- `hashtags: list[str] | None` 可选
- `upload_additional_params: dict[str, Any] | None` 可选，上传接口透传字段
- `publish_additional_params: dict[str, Any] | None` 可选，发布接口透传字段

#### 实际调用示例

下面示例展示“本地文件自动上传并发布到 TikTok”：

```json
{
	"tool": "publish_local_video_to_tiktok",
	"arguments": {
		"local_file_path": "C:/Users/raely/Videos/demo.mp4",
		"caption": "MCP auto upload test",
		"hashtags": ["mcp", "uploadpost", "tiktok"],
		"upload_additional_params": {
			"user": "zhiruipersonal",
			"platform[]": "tiktok"
		}
	}
}
```

#### Claude Desktop 推荐调用参数模板

为避免模型误判“本地文件不可访问/需要先手动转 URL”，建议在 Claude Desktop 里始终显式传以下字段：

- `local_file_path` 使用 Windows 本地绝对路径
- `user` 使用你在 Upload-Post 的 profile 用户名（例如 `zhiruipersonal`）
- `caption` 明确传入

推荐模板（可直接改值复用）：

```json
{
	"tool": "publish_local_video_to_tiktok",
	"arguments": {
		"local_file_path": "C:/Users/raely/Desktop/your_project/output/final.mp4",
		"user": "zhiruipersonal",
		"caption": "test",
		"hashtags": ["mcp", "tiktok"]
	}
}
```

建议对 Claude 的指令写法：

```text
请直接调用 MCP 工具 publish_local_video_to_tiktok，
不要先要求我提供公网 URL。
```

说明：若 Upload-Post 官方路径与你当前默认值不同，修改环境变量中的路径即可，无需改代码。