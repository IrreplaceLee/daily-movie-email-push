# 每日高分经典电影邮件推送

默认语言：中文 | [English](README.en.md)

这是 [`Automated-email-push-of-highly-rated-movies-daily`](https://github.com/IrreplaceLee/Automated-email-push-of-highly-rated-movies-daily) 的公开版。项目用于每天自动生成个性化经典电影推荐邮件：GitHub Actions 定时触发任务，Gmail API 读取观影反馈并发送邮件，DeepSeek API 负责偏好分析、电影选择和邮件文案生成。

公开版保留了核心实现、工作流、电影清单、剧照资源和演示截图；移除了真实运行历史、收件人记忆、OAuth 恢复说明、真实密钥和私有仓库提交历史。

## 公开版与私有版区别

| 对比项 | 私有版 `Automated-email-push-of-highly-rated-movies-daily` | 当前公开版 |
|---|---|---|
| 仓库可见性 | Private，用于真实运行 | Public，用于展示核心实现和运行方式 |
| 运行状态 | 保留真实 `history.json` 与 `recipient_memory.json` | 只保留 `history.example.json` 与 `recipient_memory.example.json` |
| 敏感配置 | 依赖 GitHub Secrets 和私有 OAuth 配置 | 只提供 `.env.example` 和占位变量 |
| 邮件收件人 | 使用真实收件人配置 | README 示例只使用 `recipient@example.com` |
| 工作流写权限 | 可按真实运行需要回写历史和记忆 | `contents: read`，不回写运行状态 |
| Git 历史 | 保留私有开发历史 | 使用全新的公开提交历史 |
| 剧照资源 | 保留项目使用素材 | 保留可公开展示素材，并记录来源说明 |

## 项目亮点

- 自动化调度：使用 GitHub Actions 每日定时运行。
- 邮件能力：通过 Gmail API 发送 HTML 个性化推荐邮件。
- AI 应用：使用 DeepSeek API 完成观影偏好分析、影片选择和邮件撰写。
- 个性化记忆：按收件人维护观影反馈、偏好和历史推荐，避免重复推荐。
- 本地剧照资源：`assets/stills/` 保留可公开展示的剧照素材，来源说明记录在 `assets/stills/sources.json`。
- 公开安全边界：真实 `history.json`、`recipient_memory.json` 和 `.env` 均不会提交，只保留 example 模板。

## 演示截图

| DeepSeek API 用量 | 邮箱收件箱列表 | 邮件详情页 |
|---|---|---|
| <img src="ppic/deepseek-usage-dashboard.png" alt="DeepSeek API 用量面板" width="300"> | <img src="ppic/mail-inbox-list.jpg" alt="每日电影推荐邮件收件箱列表" width="220"> | <img src="ppic/mail-detail-view.jpg" alt="电影推荐邮件详情页" width="220"> |

## 工作流程

```text
GitHub Actions 定时触发
  -> movie_mailer.py
  -> 刷新 Gmail access token
  -> 查询最近 Gmail 回复
  -> DeepSeek 分析偏好并生成推荐
  -> 组装 HTML 邮件
  -> Gmail Send API 发送
  -> 本地更新历史和记忆文件
```

公开版 workflow 不会把运行生成的 `history.json` 或 `recipient_memory.json` commit 回仓库。如果你本地运行，这两个文件只作为本地运行状态存在，并已被 `.gitignore` 忽略。

## 目录结构

```text
.
├── .github/workflows/daily-movie-email.yml
├── assets/stills/
├── docs/architecture.md
├── ppic/
├── tools/check_stills.py
├── movie_mailer.py
├── movies.json
├── history.example.json
├── recipient_memory.example.json
├── .env.example
└── SECURITY_CHECKLIST.md
```

## 必需的 GitHub Secrets

打开 `Settings` -> `Secrets and variables` -> `Actions`，添加：

```text
GMAIL_CLIENT_ID=your_google_oauth_client_id
GMAIL_CLIENT_SECRET=your_google_oauth_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
SENDER_EMAIL=your_gmail_address@gmail.com
RECIPIENT_EMAIL=recipient@example.com;friend@example.com
DEEPSEEK_API_KEY=your_deepseek_api_key
```

可选：

```text
DEEPSEEK_MODEL=deepseek-v4-pro
```

## 本地运行

```bash
python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
```

填写 `.env` 后，在本地导出对应环境变量，再运行：

```bash
python movie_mailer.py
```

## 剧照资源

公开仓库保留已有剧照资源，便于查看邮件内容组织方式。剧照来源和授权说明记录在 `assets/stills/sources.json`；只应保留有权存储和再分发的图片。

检查剧照完整性：

```bash
python tools/check_stills.py
```

## 公开边界

本公开仓库不包含：

- 真实 `history.json`
- 真实 `recipient_memory.json`
- OAuth refresh token 恢复说明
- 真实 `.env` 文件
- 原私有仓库 Git 历史
- 任何真实 API key、OAuth token、Gmail message id 或收件人记忆

## 说明

- 项目使用模型知识生成推荐文案，不声称实时联网核验电影数据库。
- 公开 workflow 日志避免打印完整收件人邮箱和 Gmail message id。
- 如果用于真实发送，请把所有密钥放在 GitHub Actions Secrets 中，不要提交运行状态文件。
