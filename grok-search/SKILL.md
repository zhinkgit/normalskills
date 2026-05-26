---
name: grok-search
description: Grok 实时联网搜索与事实核验技能，调用 scripts/grok_search.py 获取带来源链接的 JSON 研究结果。凡是用户明确要求搜索、联网、查最新、核实资料、找来源、查官网文档、查新闻、版本、价格、法规、API 变更、错误信息、模型发布、竞品资料，或问题可能因时间变化而过期时，都应积极触发；即使用户没有明说搜索，只要答案需要外部证据、当前状态或精确出处，也优先使用本技能。输出和后续总结默认使用简体中文。
---

# Grok Search

使用 Grok API 做实时联网研究，并把结果整理成带来源的 JSON。适合补充当前信息、核验事实、查找出处和对比公开资料。

## 工作流程

1. 先判断问题是否需要当前信息或外部证据；只要有明显时效性、来源要求或不确定性，就直接调用本技能。
2. 用一句清晰中文查询描述目标；必要时加入时间范围、地区、产品名、版本号、错误码、官网域名或希望优先参考的来源。
3. 运行脚本获取 JSON：

```powershell
python .\scripts\grok_search.py --query "用中文查询：OpenAI 最新模型发布和官方来源"
```

4. 阅读输出中的 `ok`、`content`、`sources`、`api_type`、`elapsed_ms`。若 `ok=false`，先把 `error/detail/config_path` 用于定位配置或接口问题。
5. 回答用户时默认使用简体中文，优先给结论，再列来源；不要把 JSON 原样倾倒给用户，除非用户明确要原始结果。

## 查询写法

- 最新状态：`"请用中文核实截至今天某项目的最新版本、发布时间和官方来源"`
- 官方文档：`"请优先搜索 example.com 官方文档，核实某 API 当前参数"`
- 错误排查：`"搜索错误信息 '...' 的近期资料，按官方 issue、文档、社区讨论排序"`
- 对比研究：`"对比 A 和 B 的当前价格/限制/发布时间，给出来源链接"`

## 配置来源

脚本按以下优先级读取配置：

1. 命令行参数：`--config`、`--base-url`、`--api-key`、`--model`
2. 环境变量：`GROK_CONFIG_PATH`、`GROK_BASE_URL`、`GROK_API_KEY`、`GROK_MODEL`
3. 技能目录：`config.json`、`config.local.json`
4. 用户目录：`~/.codex/config/grok-search.json`

可从 `config.example.json` 复制配置。不要把真实密钥写入示例文件或提交到仓库。

## API 模式

- `api_type=auto`：默认模式，根据模型名自动选择。
- `chat`：调用 `/v1/chat/completions`，适合普通 Grok 模型。
- `responses`：调用 `/v1/responses`，自动带 `web_search` tool，适合 multi-agent / responses 类模型。

## 输出字段

- `content`：综合回答，默认应为中文。
- `sources`：来源链接列表，尽量包含标题和摘要。
- `raw`：模型未按 JSON 输出时的原文。
- `reasoning`：thinking 模型返回的推理内容，通常只用于内部判断。
- `usage`、`elapsed_ms`：用量和耗时。

## 使用约束

- 对医疗、法律、金融、安全等高风险问题，搜索结果只能作为资料核验来源，回答时保留必要的不确定性。
- 若用户要求官方来源，优先核对官网、文档、公告、仓库 release 或标准组织页面。
- 若来源互相矛盾，说明冲突点和各自发布日期，不要强行合并成单一结论。
- 若请求不需要当前信息或外部证据，不要为了形式调用搜索。
