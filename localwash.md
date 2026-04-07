## 本地清洗与匹配（Local Wash & Match）设计稿

### 关键约束（不破坏现有系统）
- 尽量不改动现有工作逻辑与现有数据表字段（AI清洗/匹配链路保持不变）。
- 本地清洗与匹配采用 **新增表** 独立落库，但仍在 **现有后端项目、现有数据库连接、现有模块** 内实现（不引入新的数据库依赖/不搞独立服务）。
- 词典按 **构型（configuration_id）** 区分多份；运行时由用户在页面选择 `configuration_id`，本地清洗/匹配使用该构型绑定的词典（默认最新版本）。
- 本地清洗与匹配必须作为**独立逻辑链路**，与当前产品（AI）链路严格区分（表/接口/任务/状态独立）。
- 但在“导入公司系统”之前必须**回归现有导入链路**（殊途同归）：最终统一落到现有导入步骤与数据结构。

### Status 概念与规则（已确认）
- Status/Condition：描述里“部件怎么了/什么状态”的关键词（如 BROKEN/DIRTY/FAILED…）。
- **单值**：不允许多值；命中多个时只取一个。
- **全局词表**：Status 不绑定 Main Component。
- **不做同义词归一**：INOP/INOPERATIVE 等不合并。
- **仅英文参与**：中文暂不参与 Status（也不参与其它维度的本地抽取，先聚焦英文）。

---

## 数据表设计（新增表，独立落库；仍在现有项目/现有数据库里）

### 1) 关键词字典（按构型多份）
#### `keyword_dict`（字典头）
- `id`
- `configuration_id`：构型ID（关联现有构型表；由用户在页面选择）
- `version`：版本号/字符串（用于回溯与固化 dict_version）
- `remark`：描述（可选）
- `created_at`
- `updated_at`

> 说明：你已明确不需要 `enabled` 字段，因此字典头不做“启用/停用”标记。
> UI 展示“构型名称/机型/客户/MSN/AMM_IPC_EFF”等信息从现有构型表读取，不在字典头重复存一份（避免数据不一致）。

#### `keyword_dict_item`（字典明细）
- `id`
- `dict_id`：FK -> `keyword_dict.id`
- `dimension`：枚举 `main/sub/location/orientation/status/action`
- `main_component`：可空
  - 用于 `sub/location/orientation` 绑定到某个主部件语境（提升准确率）
  - `status/action` 维度此字段为空/忽略（因为它们是全局词表）
- `keyword`：具体关键词（英文为主）
- `enabled`：是否启用（条目级；UI 需要启停）
- `created_at`
- `updated_at`

---

### 2) 本地清洗结果（不改 workcard/defect 原表）
#### `workcard_clean_local`
- `id`
- `workcard_id`：指向现有表 `workcards.id`（内部主键）
- `aircraft_type`
- `configuration_id`：本次清洗使用的构型ID（用户选择）
- `dict_id`：本次清洗使用的字典ID（FK -> keyword_dict.id）
- `dict_version`：本次清洗使用的字典版本
- `description_en`：原始英文描述（用于追溯；你建议的命名）
- `description_cn`：原始中文描述（用于追溯；暂不参与本地抽取）
- `workcard_number`：工卡指令号（等价于 `workcards.workcard_number`，统一命名为 `workcard_number`）
- `main_component`
- `sub_component`
- `location`
- `orientation`
- `status`：单值
- `created_at`

#### `defect_clean_local`
- `id`
- `defect_record_id`：指向现有“缺陷记录”主键
- `aircraft_type`
- `configuration_id`：本次清洗使用的构型ID（用户选择）
- `dict_id`：本次清洗使用的字典ID
- `dict_version`
- `description_en`：缺陷英文描述（若没有英文则本地清洗暂不执行/留空）
- `description_cn`：缺陷中文描述（用于追溯；暂不参与本地抽取）
- `main_component`
- `sub_component`
- `location`
- `orientation`
- `status`：单值
- `created_at`

---

### 3) 本地匹配结果（候选工卡）
#### `defect_match_local`
- `id`
- `defect_record_id`
- `workcard_id`
- `aircraft_type`
- `configuration_id`：本次匹配使用的构型ID（用户选择）
- `dict_id`：本次匹配使用的字典ID
- `dict_version`
- `description_en`：缺陷英文描述（用于展示/导出，可选冗余）
- `description_cn`：缺陷中文描述（用于展示/导出，可选冗余）
- `workcard_number`：候选工卡指令号（来自 `workcards.workcard_number`，统一命名为 `workcard_number`）
- `score_total`：0~100
- `score_main`：0/35
- `score_action`：0/5
- `created_at`

> 说明：存分项分数可以直接解释“为什么这条达标/不达标”，前端无需二次计算。

---

## 工作逻辑（端到端流程）

### 0) 隔离与回归（殊途同归：独立链路，但最终出口一致）
- **隔离边界**：
  - 本地清洗/匹配只写入本文档定义的本地表（`keyword_dict* / workcard_clean_local / defect_clean_local / defect_match_local`），不写/不改现有 AI 链路的清洗/匹配结果表与字段。
  - 本地链路使用独立的 API 路由与服务方法（命名上显式包含 `local`），避免误调用现有产品逻辑。
  - 前端通过“模式选择（AI / 本地）”切换数据源与调用入口，AI 模式保持原行为。

- **回归点（最终出口）**：
  - 在用户完成本地匹配并人工确认候选后，**回归到现有“导入公司系统”前的保存步骤**：把用户选中的候选转换为现有导入数据结构，写入现有导入表（`import_batches / import_batch_items`）。
  - 之后的“批量导入调试/对接公司系统执行导入”步骤完全复用现有页面与现有逻辑，不做分叉。

- **适配器（本地结果 -> 现有导入结构）**：
  - 输入：`defect_match_local` 中用户勾选/确认的候选（`defect_record_id + workcard_id + workcard_number + score_total` 等）
  - 输出：构造现有 `importBatchApi.create(...)` 所需 payload，并落库到 `import_batches/import_batch_items`（字段映射在实施阶段按现有接口约定对齐）。

- **最终回归的“匹配后工卡数据表字段口径”（必须与现有产品一致）**：
  - 本地链路内部字段命名也统一使用 `workcard_number`，与现有 `import_batch_items` 字段保持一致，避免二次转换出错。
  - 现有导入条目字段（`import_batch_items` / `ImportBatchItemCreate`）如下：
    - `defect_record_id`：缺陷记录ID
    - `defect_number`：缺陷编号
    - `description_cn`：中文描述
    - `description_en`：英文描述
    - `workcard_number`：候选工卡指令号（来自本地候选的 `workcard_number`）
    - `selected_workcard_id`：选中的候选工卡ID（如本地有对应 `workcard_id` 可映射，否则可空）
    - `similarity_score`：相似度/评分（本地 `score_total` → 这里，范围 0~100）
    - `issued_workcard_number`：已开出的工卡号（如无则按现有逻辑可留空/NR/000）
    - `reference_workcard_number`：相关工卡号（如有）
    - `reference_workcard_item`：相关工卡序号（如有）
    - `area`：区域（如有）
    - `zone_number`：区域号（如有）

### A) 关键词管理（CRUD UI）
- 参考现有“构型数据库模式”，把构型关键词数据表按行展示，供用户选择。
- 支持导入/导出 Excel/CSV（导出 CSV 需 `utf-8-sig` 兼容中文）。
- 在线编辑：支持条目增删改查、启停（`keyword_dict_item.enabled`）。
- 版本策略：同一构型（configuration_id）可多版本并存；默认使用最新版本（version 最大/或 created_at 最新）。清洗/匹配时写入 `dict_version` 便于回溯。

### B) 本地清洗引擎（历史工卡）
输入：历史工卡数据中的 `description_en/description_cn`（以及 workcard_id、aircraft_type），并由用户选择 `configuration_id`。

输出：写入 `workcard_clean_local`（结构化 5 维 + configuration_id + dict_id/dict_version + description_en/description_cn）。

规则（与 AI 流程独立）：
- 先识别 `main_component`（主部件，多值，逗号分隔，所有匹配的关键词）
- 在主部件语境下识别：`sub_component`（多值）、`location`、`orientation`
- `status` 用全局状态词表识别（不绑定 main）
- `action` 用全局动作词表识别（不绑定 main）
- Status 单值：命中多个时仅取一个
 - Action 单值：命中多个时仅取一个（最长关键词优先）

### C) 本地清洗（缺陷）
输入：新增缺陷 `description_en/description_cn`（defect_record_id、aircraft_type），并由用户选择 `configuration_id`。

输出：写入 `defect_clean_local`。

### D) 本地匹配（阈值与权重已确认）
对每条 `defect_clean_local` 与 `workcard_clean_local` 做维度比对打分：
- main 匹配策略（多值）：
  * 完全匹配（所有关键词都匹配）：+32.55
  * 匹配到 2 个及以上关键词：+30.0
  * 匹配到 1 个关键词：+25.0
  * 只有一方有：+20.0
- sub 相同：+50
- location 相同：+3
- orientation 相同：+2
- status 相同：+5
- action 相同：+5
- 总分满分 100

阈值：
- `score_total >= 90` 记为“匹配成功候选工卡”

输出：
- 将候选写入 `defect_match_local`（含分项分数与总分），供前端展示/人工选择。

---

## 已确认清单（最终口径）

### 1) 字段语义与来源
- `workcard_clean_local.workcard_id = workcards.id`
- `workcard_number = workcards.workcard_number`（字段统一命名为 `workcard_number`）
- `defect_match_local.workcard_number` 表示“候选工卡的工卡指令号”（来自 `workcards.workcard_number`）

### 2) 字典版本与审计
- `keyword_dict` 增加 `version`，用于 `dict_version` 回溯
- `keyword_dict` 增加 `created_at/updated_at`

### 3) 关键词条目启停
- 保留 `keyword_dict_item.enabled`（UI 需要启停）

### 4) Status 单值取法
- 命中多个 status 时：最长关键词优先（通常每行只有一个 status）

### 5) 匹配结果落库策略
- `defect_match_local` 只存 `score_total >= 90` 的候选（需要调整再改阈值）

### 6) 词典选择策略
- 用户在页面选择一个构型（`configuration_id`），本地清洗/匹配使用该构型绑定的词典（默认最新版本）

### 7) 英文/中文字段命名
- 建议统一命名：`description_en` / `description_cn`

### 8) 缺失字段处理
- `sub_component` 缺失，甚至 `main_component` 缺失：定义为匹配错误（不产生候选）


