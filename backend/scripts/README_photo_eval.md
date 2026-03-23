# 图片检索评测脚本（TOP1相关率 / 视觉幻觉过滤 / 零召回率）

## 1) 准备样本

复制模板并填写你的景点样本：

- 模板文件：[scripts/data/photo_eval_samples.example.json](data/photo_eval_samples.example.json)
- 建议复制为：`scripts/data/photo_eval_samples.json`

字段说明：

- `id`: 样本ID（可选，建议唯一）
- `name`: 景点名称（必填）
- `city`: 城市（可选）
- `category`: 类别（可选）

> 当前版本已改为“视觉大模型判定”，不再依赖 `judge_tokens` 文本比对。

## 2) 运行评测

在 `backend` 目录执行：

```bash
python scripts/eval_unsplash_metrics.py --dataset scripts/data/photo_eval_samples.json
```

常用参数：

- `--baseline-mode name|name_city`：基线查询方式（默认 `name`，对应“原始API按景点名检索”）
- `--judge-base-url`：视觉判定模型的 OpenAI 兼容地址（默认读取 `LLM_BASE_URL`）
- `--judge-api-key`：视觉判定模型的 API Key（默认读取 `LLM_API_KEY` / `OPENAI_API_KEY`）
- `--judge-model`：视觉模型ID（默认读取 `LLM_VISION_MODEL_ID`，否则 `LLM_MODEL_ID`）
- `--judge-timeout`：视觉模型超时秒数
- `--heuristic-policy raw|balanced`：启发式评测策略（默认 `balanced`，会在启发式空结果时回退基线相关图，并仅对低置信度幻觉进行过滤）
- `--low-confidence-threshold 0.28`：仅在 `balanced` 下生效；当视觉判定为幻觉且置信度低于阈值时才过滤为零召回
- `--sleep-seconds 0.0`：每个样本间隔（防限流）
- `--out-dir scripts/out`：输出目录

## 3) 输出结果

脚本会生成：

- `summary_*.json`：汇总指标
- `details_*.csv`：逐样本明细

关键指标：

- `baseline_top1_relevance_rate`：原始API的TOP1相关率
- `heuristic_top1_relevance_rate`：启发式算法的TOP1相关率
- `baseline_zero_recall_rate`：原始API零召回率
- `heuristic_zero_recall_rate`：启发式算法零召回率
- `strict_filter_ratio_on_baseline_hallucinations`：基于“原始API视觉幻觉样本”被启发式直接过滤（返回None）的比例
- `mitigation_ratio_on_baseline_hallucinations`：基于“原始API视觉幻觉样本”被启发式消解（过滤或替换为相关图）的比例
