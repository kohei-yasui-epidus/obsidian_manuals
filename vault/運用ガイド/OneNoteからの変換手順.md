---
title: OneNoteからの変換手順
category: 運用ガイド
tags:
  - システム
created: 2026-07-02
updated: 2026-07-02
---

# OneNote からの変換手順(変換担当者向け)

OneNote のマニュアルを Markdown に変換して Vault に取り込む手順です。

## 事前準備(初回のみ)

```bash
cd obsidian_manuals
bash tools/setup.sh
```

pandoc / cabextract / one2html が自動でインストールされます(Homebrew必須)。

## 1. OneNote からファイルを取り出す

### 方法A: セクション単位でエクスポート(.one)

- **OneNote 2016 (Windows)**: ファイル → エクスポート → セクション → 「OneNote 2010-2016 セクション (*.one)」
- **OneDrive上のノートブック**: OneDrive のWeb画面でノートブックを右クリック → ダウンロード(セクションごとの .one が入手できます)

### 方法B: ノートブック丸ごと(.onepkg)

- OneNote 2016: ファイル → エクスポート → ノートブック → 「OneNote パッケージ (*.onepkg)」

### 方法C: フォールバック(.docx)

.one の解析に失敗するページがある場合:

- OneNote: ファイル → エクスポート → ページ/セクション → 「Word 文書 (*.docx)」

> [!warning] Mac版OneNoteについて
> Mac版OneNoteにはエクスポート機能がほぼありません。エクスポートは **Windows版 OneNote** か **OneDrive Web** から行ってください。

## 2. 変換を実行

取り出したファイルを `input/` フォルダに置いて:

```bash
python3 tools/convert.py
```

- 出力先: `vault/マニュアル/<ファイル名>/<ページ名>.md`
- 画像・添付は `vault/添付ファイル/` に自動集約
- 新規・更新があると `vault/通達/` に **通達ノートが自動生成** されます

### 便利なオプション

```bash
python3 tools/convert.py --category 経理部        # 出力カテゴリを指定
python3 tools/convert.py --dry-run                # 何が起きるか事前確認
python3 tools/convert.py --no-announce            # 通達を生成しない
python3 tools/convert.py --push                   # 変換後そのまま commit & push
python3 tools/convert.py 個別ファイル.one          # ファイル指定
```

## 3. 結果を確認して共有

1. Obsidian で変換結果を開き、レイアウト崩れ・画像抜けがないか確認
2. frontmatter の `category` や `status` を必要に応じて修正
3. push(`--push` を使わなかった場合):
   ```bash
   git add vault && git commit -m "マニュアル追加: ○○" && git push
   ```

チームメンバーには Obsidian Git の自動 pull(10分間隔)で届き、[[Home]] の「📣 通達」「🆕 新着」に表示されます。

## 変換の仕組み

```
.onepkg ──cabextract──> .one ──one2html──> HTML ──pandoc──> Markdown
.docx ────────────────────────────pandoc──────────────────> Markdown
```

同じページを再変換しても内容が変わっていなければスキップされます(created日付も保持)。
