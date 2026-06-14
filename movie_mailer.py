import base64
import json
import os
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import requests


GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"
HISTORY_PATH = Path("history.json")
MEMORY_PATH = Path("recipient_memory.json")
RECENT_HISTORY_LIMIT = 30


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def parse_recipients(value):
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def mask_email(value):
    if "@" not in value:
        return "<recipient>"
    name, domain = value.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[:1]}***@{domain}"


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_access_token():
    response = requests.post(
        GMAIL_TOKEN_URL,
        data={
            "client_id": require_env("GMAIL_CLIENT_ID"),
            "client_secret": require_env("GMAIL_CLIENT_SECRET"),
            "refresh_token": require_env("GMAIL_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not response.ok:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"raw_response": response.text}
        raise RuntimeError(
            "Failed to refresh Gmail access token: "
            f"HTTP {response.status_code}; "
            f"error={error_payload.get('error', '<missing>')}; "
            f"description={error_payload.get('error_description', '<missing>')}"
        )
    return response.json()["access_token"]


def gmail_request(method, path, token, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        f"{GMAIL_API_BASE}{path}",
        headers=headers,
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def decode_base64url(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="ignore")


def decode_message_body(payload):
    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data and mime_type in {"text/plain", "text/html", ""}:
        return decode_base64url(data)
    for preferred in ("text/plain", "text/html"):
        for part in payload.get("parts", []):
            if part.get("mimeType") == preferred:
                text = decode_message_body(part)
                if text:
                    return text
    for part in payload.get("parts", []):
        text = decode_message_body(part)
        if text:
            return text
    return ""


def strip_quoted_reply(body):
    body = re.sub(r"<[^>]+>", " ", body)
    splitters = [
        "--------------原始邮件--------------",
        "On ",
        "发件人:",
        "From:",
        "-----Original Message-----",
    ]
    first_part = body
    for splitter in splitters:
        first_part = first_part.split(splitter)[0]
    return " ".join(first_part.split())[:1200]


def latest_user_reply(token, recipient):
    query = (
        f'from:{recipient} newer_than:1d '
        '(subject:"每日高分经典电影推荐" OR 电影 OR 影评 OR 观后感 OR 推荐 OR 类型 OR 想看 OR 回复)'
    )
    result = gmail_request("GET", "/messages", token, params={"q": query, "maxResults": 10})
    ignored = {"收到", "已收到", "好的", "谢谢", "ok", "OK"}
    for item in result.get("messages", []):
        message = gmail_request("GET", f"/messages/{item['id']}", token)
        body = strip_quoted_reply(decode_message_body(message.get("payload", {})))
        if len(body) >= 6 and body not in ignored:
            return {
                "message_id": item["id"],
                "text": body,
                "received_at": message.get("internalDate"),
            }
    return {"message_id": "", "text": "", "received_at": ""}


def deepseek_json(messages, max_tokens=5000):
    response = requests.post(
        DEEPSEEK_CHAT_URL,
        headers={
            "Authorization": f"Bearer {require_env('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    if response.status_code == 401:
        raise RuntimeError(
            "DeepSeek API authentication failed with 401 Unauthorized. "
            "Check the GitHub secret DEEPSEEK_API_KEY: paste the API key exactly, "
            "without quotes, spaces, or a DEEPSEEK_API_KEY= prefix."
        )
    if response.status_code == 402:
        raise RuntimeError("DeepSeek API billing failed with 402. Check the account balance.")
    if response.status_code == 429:
        raise RuntimeError("DeepSeek API rate limit reached. Retry later or check account limits.")
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"DeepSeek API request failed: {response.status_code} {response.text[:800]}") from exc
    content = response.json()["choices"][0]["message"]["content"].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def history_for(history, recipient):
    if "recipients" not in history:
        migrated = {}
        for item in history.get("sent", []):
            for old_recipient in item.get("recipients", []):
                migrated.setdefault(old_recipient, {"sent": []})["sent"].append(item)
        history.clear()
        history["recipients"] = migrated
    return history.setdefault("recipients", {}).setdefault(recipient, {"sent": []})


def build_deepseek_payload(recipient, reply, memory, user_history):
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    recent_movies = [
        {
            "title": item.get("title"),
            "original_title": item.get("original_title"),
            "sent_at": item.get("sent_at"),
        }
        for item in user_history.get("sent", [])[-RECENT_HISTORY_LIMIT:]
    ]
    return {
        "recipient": recipient,
        "current_time": now,
        "yesterday_reply": reply.get("text", ""),
        "recipient_memory": memory,
        "recent_recommendation_history": recent_movies,
        "requirements": {
            "task": "只基于 DeepSeek 模型知识完成用户影评分析、偏好判断、经典电影选择和邮件撰写；不调用外部电影数据库或搜索 API。",
            "scope": "只处理电影推荐、观影反馈、影评、类型偏好、电影相关问题。",
            "off_topic_policy": "如果用户提出与电影推荐无关的要求，要简短拒绝，并自然回到电影推荐。",
            "avoid_repeats": "不要推荐 recent_recommendation_history 中出现过的电影。",
            "verification_policy": "由于本流程不联网实时检索，不要声称已经实时核验；对评分和资料写成“DeepSeek 基于模型知识整理，未联网实时核验”。",
            "image_policy": "不要编造剧照链接，不要输出远程 img 标签。剧照部分说明：本版本不接入外部图库，因此暂不内嵌剧照。",
        },
        "json_schema": {
            "subject": "每日高分经典电影推荐：<电影名称>",
            "html_body": "完整 HTML body 内部片段",
            "selected_movie": {
                "title": "中文片名",
                "original_title": "原片名",
                "region": "国家/地区",
                "year": "年份",
                "director": "导演",
                "cast": "主要演员",
                "douban_rating": "豆瓣评分或未联网实时核验说明",
                "runtime": "片长",
            },
            "memory_update": {
                "preferences": ["电影相关偏好"],
                "disliked_preferences": ["不喜欢的电影相关元素"],
                "recent_feedback_summary": "用户最近电影反馈摘要",
                "next_watch_requests": ["下一次想看的电影方向"],
                "off_topic_notes": ["与电影推荐无关请求的简短记录"],
            },
            "handled_reflection": "boolean",
            "rejected_off_topic": "boolean",
        },
    }


def compose_email_with_deepseek(recipient, reply, memory, user_history):
    system_prompt = """
你是每日经典电影推荐邮件作者和私人观影记忆助手。请只输出 JSON，不要输出 Markdown。

硬性规则：
1. 只处理电影推荐、观影反馈、影评、类型偏好和电影相关问题。
2. 用户提出无关请求时，在邮件开头温和拒绝，不执行、不展开，然后回到电影推荐。
3. 不使用外部 API、不要声称已实时联网检索。
4. 可以基于模型知识选择高分经典电影，但必须在邮件中写明“资料由 DeepSeek 基于模型知识整理，未联网实时核验”。
5. 不要编造剧照链接。剧照部分必须说明“本版本不接入外部图库，暂不内嵌剧照”。
6. 避免推荐历史中已经出现过的电影。
7. 评论只能是短摘录或高度概括，不能大段复制受版权保护内容。

HTML 正文必须包含：
- 如果有用户回复：先具体回应用户观点，分析电影主题、人物、镜头、叙事或情绪表达。
- 推荐电影名称、原片名、国家/地区、年份、导演、主要演员、豆瓣评分或核验说明、片长、简介。
- 为什么值得观看的一段分析。
- 剧照说明。
- 4 条经典评论摘录/高度概括。
- 资料说明和当前生成时间。
""".strip()
    payload = build_deepseek_payload(recipient, reply, memory, user_history)
    result = deepseek_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        max_tokens=6000,
    )
    selected_movie = result.get("selected_movie") or {}
    title = selected_movie.get("title") or "经典电影"
    result.setdefault("subject", f"每日高分经典电影推荐：{title}")
    result.setdefault("html_body", fallback_html(title))
    result.setdefault("selected_movie", {"title": title, "original_title": ""})
    result.setdefault("memory_update", {})
    result.setdefault("handled_reflection", bool(reply.get("text")))
    result.setdefault("rejected_off_topic", False)
    return result


def fallback_html(title):
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return f"""
    <p>你好，今天推荐一部值得反复观看的经典电影：{title}。</p>
    <p>本版本只使用 DeepSeek 基于模型知识整理内容，未联网实时核验电影资料。</p>
    <p><strong>剧照：</strong>本版本不接入外部图库，因此暂不内嵌剧照。</p>
    <p><strong>生成时间：</strong>{generated_at}</p>
    """


def wrap_html(body):
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    if "未联网实时核验" not in body:
        body += "<hr><p><strong>资料说明：</strong>本邮件由 DeepSeek 基于模型知识整理，未联网实时核验。</p>"
    if "生成时间" not in body:
        body += f"<p><strong>生成时间：</strong>{generated_at}</p>"
    return f"""
    <html>
      <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.65;color:#202124;">
        {body}
      </body>
    </html>
    """


def send_email(token, sender, recipient, subject, html):
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content("请使用支持 HTML 的邮箱客户端查看本期电影推荐。")
    message.add_alternative(html, subtype="html")
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return gmail_request(
        "POST",
        "/messages/send",
        token,
        headers={"Content-Type": "application/json"},
        json={"raw": raw},
    )


def merge_memory(existing, update, sent_movie):
    merged = dict(existing or {})
    for key in ("preferences", "disliked_preferences", "next_watch_requests", "off_topic_notes"):
        values = list(merged.get(key, []))
        for value in update.get(key, []):
            if value and value not in values:
                values.append(value)
        merged[key] = values[-30:]
    if update.get("recent_feedback_summary"):
        merged["recent_feedback_summary"] = update["recent_feedback_summary"]
    recommended = list(merged.get("recommended_movies", []))
    recommended.append(sent_movie)
    merged["recommended_movies"] = recommended[-RECENT_HISTORY_LIMIT:]
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    return merged


def process_recipient(token, sender, recipient, history, memory):
    user_history = history_for(history, recipient)
    user_memory = memory.setdefault("recipients", {}).setdefault(recipient, {})
    reply = latest_user_reply(token, recipient)
    email = compose_email_with_deepseek(recipient, reply, user_memory, user_history)
    selected_movie = email.get("selected_movie", {})
    title = selected_movie.get("title", "经典电影")
    subject = email.get("subject") or f"每日高分经典电影推荐：{title}"
    if not subject.startswith("每日高分经典电影推荐："):
        subject = f"每日高分经典电影推荐：{title}"
    html = wrap_html(email.get("html_body") or fallback_html(title))
    send_result = send_email(token, sender, recipient, subject, html)
    sent_movie = {
        "title": title,
        "original_title": selected_movie.get("original_title", ""),
        "region": selected_movie.get("region", ""),
        "year": selected_movie.get("year", ""),
        "director": selected_movie.get("director", ""),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "gmail_message_id": "",
        "handled_reflection": bool(email.get("handled_reflection")),
        "rejected_off_topic": bool(email.get("rejected_off_topic")),
        "reply_message_id": "",
        "source_mode": "deepseek_model_knowledge_without_live_verification",
    }
    user_history.setdefault("sent", []).append(sent_movie)
    memory["recipients"][recipient] = merge_memory(user_memory, email.get("memory_update", {}), sent_movie)
    return {
        "recipient": recipient,
        "sent": title,
        "gmail_message_id": "",
        "handled_reflection": bool(email.get("handled_reflection")),
        "rejected_off_topic": bool(email.get("rejected_off_topic")),
        "source_mode": sent_movie["source_mode"],
    }


def main():
    recipients = parse_recipients(require_env("RECIPIENT_EMAIL"))
    if not recipients:
        raise RuntimeError("RECIPIENT_EMAIL did not contain any valid recipient")
    sender = require_env("SENDER_EMAIL")
    token = get_access_token()
    history = load_json(HISTORY_PATH, {"recipients": {}})
    memory = load_json(MEMORY_PATH, {"recipients": {}})
    results = []
    for recipient in recipients:
        results.append(process_recipient(token, sender, recipient, history, memory))
    save_json(HISTORY_PATH, history)
    save_json(MEMORY_PATH, memory)
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
