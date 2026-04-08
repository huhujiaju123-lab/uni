# knowledge-知识库

这个目录承接跨项目的知识、阅读与参考资料，不放长期维护的可执行项目源码。

## 当前结构

- `obsidian-知识图谱/`
  - 来自 `/Users/xiaoxiao/Obsidian/KnowledgeOS`
  - 保留知识内容、MOC、模板与项目笔记
  - 不纳入 `.obsidian/` 应用配置
- `calibre-阅读资料/`
  - 来自 `/Users/xiaoxiao/Calibre Library`
  - 仅保留可版本化的书籍目录导出
  - 不纳入 `metadata.db`、`.calnotes/` 等应用状态
- `sql-资料库/`
  - 来自桌面 `sql/`
  - 作为可复用查询与资料归档
- `reference-参考归档/`
  - 放转录、终端输出、调试记录、桌面临时资料等

## 使用规则

1. 知识内容在这里沉淀，正式项目源码仍然回到各自一级目录。
2. Obsidian 项目笔记应通过 README/MOC 链到对应代码目录，不要替代代码项目本身。
3. 新增阅读资料时，优先导出为 Markdown 或结构化文本，再纳入此目录。
