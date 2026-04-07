# txtZoneName 和 txtZoneTen 数据来源说明

## 当前代码中的数据来源

### 1. txtZoneName（区域名称）

**当前实现**：
- **代码位置**：`frontend/src/pages/EnglishBatchImportDebug.tsx` 的 `buildEnglishImportParams` 函数
- **当前值**：强制设置为固定值 `'%BB%FA%C9%CF'`（URL编码的"机上"）
- **代码**：
  ```typescript
  const REQUIRED_ZONE_NAME = '%BB%FA%C9%CF'
  txtZoneName: REQUIRED_ZONE_NAME,
  ```

**数据来源优先级（已废弃，当前不使用）**：
1. ~~`record.area`~~ - 来自表格"缺陷匹配结果与候选工卡"的"区域"列（已废弃）
2. ~~`importParams.txtZoneName`~~ - 来自表单"其他参数"区域的 `txtZoneName` 字段（已废弃）
3. ~~空字符串 `""`~~ - 默认值（已废弃）

**表单中的字段**：
- 位置：`其他参数 (可折叠或保持默认)` 区域
- 字段名：`Zone Name (txtZoneName)`
- 默认值：`"%BB%FA%C9%CF"`（在 `loadImportBatch` 函数中设置）
- **注意**：虽然表单中有这个字段，但代码中不再使用它的值，因为强制设置为固定值

**表格中的字段**：
- 位置：`缺陷匹配结果与候选工卡` 表格
- 列名：`区域`
- 数据字段：`record.area`
- **注意**：虽然表格中有这个字段，但代码中不再使用它来设置 `txtZoneName`

---

### 2. txtZoneTen（区域号）

**当前实现**：
- **代码位置**：`frontend/src/pages/EnglishBatchImportDebug.tsx` 的 `buildEnglishImportParams` 函数
- **当前值**：`record.txtZoneTen || importParams.txtZoneTen || ""`
- **代码**：
  ```typescript
  txtZoneTen: record.txtZoneTen || importParams.txtZoneTen || "",
  ```

**数据来源优先级**：
1. **`record.txtZoneTen`** - 来自表格"缺陷匹配结果与候选工卡"的"区域号"列（**主要来源**）
   - 数据库字段：`import_batch_items.zone_number`
   - 表格列名：`区域号`
   - 数据字段：`MatchResult.txtZoneTen`
   
2. **`importParams.txtZoneTen`** - 来自表单"其他参数"区域的 `txtZoneTen` 字段（**备选来源**）
   - **注意**：表单中**没有** `txtZoneTen` 字段！
   - 所以这个备选来源实际上不起作用
   
3. **空字符串 `""`** - 默认值（如果前两者都为空）

**表格中的字段**：
- 位置：`缺陷匹配结果与候选工卡` 表格
- 列名：`区域号`
- 数据字段：`record.txtZoneTen`
- 数据库字段：`import_batch_items.zone_number`
- **数据来源**：
  - Excel导入时：来自Excel的 `区域号` / `Zone` / `Zone Number` 列
  - 数据库加载时：来自 `import_batch_items.zone_number` 字段

**表单中的字段**：
- **不存在**：表单"其他参数"区域中**没有** `txtZoneTen` 字段
- 所以 `importParams.txtZoneTen` 永远是 `undefined`

---

## 数据流图

### txtZoneName 数据流

```
固定值 '%BB%FA%C9%CF'
    ↓
buildEnglishImportParams()
    ↓
强制设置为 REQUIRED_ZONE_NAME
    ↓
POST 请求参数 txtZoneName
```

**注意**：表单中的 `txtZoneName` 字段和表格中的 `area` 字段都不再使用。

---

### txtZoneTen 数据流

```
Excel导入 / 数据库加载
    ↓
MatchResult.txtZoneTen
    ↓
buildEnglishImportParams()
    ↓
record.txtZoneTen || importParams.txtZoneTen || ""
    ↓
（实际上只使用 record.txtZoneTen，因为表单中没有 txtZoneTen 字段）
    ↓
POST 请求参数 txtZoneTen
```

---

## 总结

### txtZoneName
- **来源**：代码中强制设置的固定值 `'%BB%FA%C9%CF'`
- **不来自**：表格数据或表单参数（虽然表单中有字段，但不使用）

### txtZoneTen
- **主要来源**：表格"缺陷匹配结果与候选工卡"的"区域号"列（`record.txtZoneTen`）
- **备选来源**：表单"其他参数"区域的 `txtZoneTen` 字段（**但表单中没有这个字段**）
- **实际使用**：只使用表格数据 `record.txtZoneTen`

---

## 建议

如果要让 `txtZoneTen` 也能从表单获取默认值，需要：
1. 在表单"其他参数"区域添加 `txtZoneTen` 字段
2. 在 `loadImportBatch` 函数中设置默认值



