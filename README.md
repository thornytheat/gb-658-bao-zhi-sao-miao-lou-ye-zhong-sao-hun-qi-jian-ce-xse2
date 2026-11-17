# 扫描期版质检台

面向真实数据复核的中型数据工程工具，包含六个可独立调用的业务模块。规则、失败原因与证据字段见 docs/DATA-DICTIONARY.md，陷阱和测试映射见 docs/DEPTH.md。

## 启动

docker compose up --build

浏览器访问 http://localhost:18217。测试：docker compose exec -T app pytest -q

## 模块

- M1 清单采信：页面 /intake，接口 /api/scans/import
- M2 期版契约：页面 /issues，接口 /api/issues/normalize
- M3 页码序列：页面 /pages，接口 /api/pages/check
- M4 重扫判定：页面 /rescans，接口 /api/rescans/evaluate
- M5 混期归因：页面 /mixed，接口 /api/mixed/evaluate
- M6 批次对账：页面 /batches，接口 /api/reconcile
- M7 结算补扣：页面 /settle，接口 /api/settle/statements（结算/回读）、/sign（签收）、/corrections（更正）

## 运行规则

同一输入内容生成相同运行标识，重复执行复用已有批次。隔离记录包含原因码、原始行号与原值；业务导出只保留一份证据清单。

结算按站点约定单价与采纳页生成结算单，重复扫描与未裁决件不计费。签收后结算单冻结为付款凭据，复核更正另记补扣差额，旧单与原依据保留；更正携带基准版本，过期拒绝；差额两段落账，中断恢复、重试均不重复补扣；对账核对原付、调整与当前应付。不做实际付款。

