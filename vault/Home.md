---
title: Home
tags:
  - システム
---

# 📚 マニュアルポータル

> [!tip] 使い方
> - **全文検索**: `Cmd + Shift + F`(コマンドパレット `Cmd + P` から「Omnisearch」も利用可)
> - **タイトルから開く**: `Cmd + O`
> - **カテゴリから探す**: 左のファイルツリー →「マニュアル」フォルダ
> - 初めての方は **[[はじめに(セットアップ)]]** をお読みください

---

## 📣 通達・お知らせ

```dataview
TABLE WITHOUT ID file.link AS "通達", date AS "日付", type AS "種別"
FROM "通達"
SORT date DESC, file.name DESC
LIMIT 10
```

## 🆕 新着マニュアル(30日以内)

```dataview
TABLE WITHOUT ID file.link AS "マニュアル", category AS "カテゴリ", created AS "作成日"
FROM "マニュアル"
WHERE created >= date(today) - dur(30 days)
SORT created DESC
```

## 🔄 最近更新されたマニュアル(30日以内)

```dataview
TABLE WITHOUT ID file.link AS "マニュアル", category AS "カテゴリ", updated AS "更新日"
FROM "マニュアル"
WHERE updated >= date(today) - dur(30 days) AND updated != created
SORT updated DESC
LIMIT 15
```

## 🗂 カテゴリ別

```dataview
TABLE length(rows) AS "件数"
FROM "マニュアル"
GROUP BY category AS "カテゴリ"
SORT length(rows) DESC
```

---

📖 **[[マニュアル一覧]]** — 全マニュアルの一覧表はこちら
🛠 **[[OneNoteからの変換手順]]** / **[[新規マニュアルの作成手順]]** / **[[チーム運用ルール(Git同期)]]**
