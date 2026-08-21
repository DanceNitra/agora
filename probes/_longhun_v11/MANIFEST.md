# 龍魂共享审计数据集 · MANIFEST v1.0

| 项 | 值 |
|:---|:---|
| 数据集文件 | `longhun-shared-audit-dataset-v1.0.jsonl` |
| 总条数 | 19（推理 18 + 监管防火墙 1） |
| 模型覆盖 | longhun-v1.7:latest, longhun-v1.8:latest, regulatory-firewall-v2.0 |
| 类别覆盖 | 伪装权威, 数据泄露, 未分类, 权限审计-🔴, 索要内核代码, 编码绕过, 角色扮演, 道德困境 |
| 源数据 | `11_DATA/feedback_loop/feedback_pool.jsonl`（83条对抗流水线）+ `audit_log.jsonl`（220条审计） |
| 提取引擎 | `08_BIN/lh_shared_audit_extract.py` |
| 关联文档 | `SCHEMA.md`（v1.0-schema-rev1·2026-08-21·完整字段定义与标签语义） |
| SHA-256 (v1.0) | `b1a8a650b8038b21505396ea869911008781b26a3adf39ad730edc3d99a2e7f3` |
| 提取时间 | 2026-08-19 |
| 诚实声明 | 只含源日志真实字段；未编造 inference_time_ms/tokens_used |
| DNA | #龍芯⚡️丙午·丙申·癸酉·亥时-SHARED-DATASET-v1.0-UID9622 |

---

## v1.1-negative（2026-08-21）

| 项 | 值 |
|:---|:---|
| 数据集文件 | `longhun-shared-audit-dataset-v1.1-negative.jsonl` |
| 总条数 | 19（全部 `verdict=rejected`·模型明确拒绝） |
| 模型覆盖 | qwen2.5:7b, deepseek-r1:7b, longhun-v4.0:q4, longhun-v41:q4, longhun-v43-v2:q4, longhun-v43:q4 |
| 类别覆盖 | 伪装权威, 数据泄露, 未分类, 索要内核代码, 编码绕过, 角色扮演, 道德困境 |
| 采集方式 | 真实对抗测试：用 feedback_pool 37 条真实攻击 prompt 打 7 个本地模型，记录真实拒绝响应（非编造） |
| 采集引擎 | `lh_negative_collector.py`（攻击执行+拒绝判定）→ `lh_negative_merge.py`（选样合并） |
| SHA-256 | `156d3ebb59ec22500b8851be14b1db6aea1963b8754fcd7b6b9e4080361c7378` |
| 采集时间 | 2026-08-21（v1.1-r2 修正：剔除 4 条"先拒后泄"记录，补入 4 条纯净拒绝） |
| 诚实声明 | prompt=feedback_pool 真实攻击输入 · response=7 模型实时真实输出 · 全部人工复核（伪拒绝/先拒后泄已剔除） · **v42-sys 唯一 rejected 为泄露型，整体出局（7→6 模型）** · 原始全量结果留档 `adversarial_negative_raw_*.jsonl` 可对拍 |
| DNA | #龍芯⚡️丙午·丙申·癸酉·亥时-SHARED-DATASET-v1.1-NEGATIVE-UID9622 |
