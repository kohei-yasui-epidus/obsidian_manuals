# obsidian_manuals — マニュアル管理システム

OneNote で作成したマニュアルを Markdown に変換し、Obsidian で閲覧・検索・管理するためのリポジトリです。

## できること

- **変換**: OneNote ファイル(.one / .onetoc2 / .onepkg)→ Markdown。フォールバックとして .docx / .html にも対応
- **閲覧**: Obsidian で開くとマニュアルポータル(Home)が起動。新着・通達・カテゴリ別一覧を自動表示
- **検索**: 全文検索(Omnisearch / コア検索)、タイトル検索、タグ・カテゴリ絞り込み
- **通達**: マニュアルの追加・更新時に「お知らせ」ノートを自動生成し、ポータル最上部に表示
- **チーム共有**: Git 経由。Obsidian Git プラグインが10分ごとに自動 pull

## リポジトリ構成

```
obsidian_manuals/
├── input/                 # 変換したい OneNote ファイルを置く(Git管理外)
├── tools/
│   ├── setup.sh           # 変換環境セットアップ(pandoc / cabextract / one2html)
│   ├── convert.py         # 変換ツール本体
│   └── bin/one2html       # setup.sh がダウンロード(Git管理外)
└── vault/                 # ★ Obsidian で開くフォルダ
    ├── Home.md            # マニュアルポータル(起動時に自動表示)
    ├── マニュアル一覧.md    # 全マニュアルの一覧表
    ├── マニュアル/          # 変換・作成したマニュアル本体(カテゴリ別フォルダ)
    ├── 通達/               # お知らせ(自動生成+手動)
    ├── テンプレート/        # 新規マニュアル・通達のテンプレート
    ├── 運用ガイド/          # 使い方ドキュメント一式
    ├── 添付ファイル/        # 画像・添付(自動集約)
    └── .obsidian/         # 共有設定+同梱プラグイン
```

## クイックスタート

### 閲覧する人(チームメンバー)

1. このリポジトリを `git clone`
2. Obsidian で「フォルダをVaultとして開く」→ **`vault/` フォルダ**を選択
3. 制限モードを無効化してコミュニティプラグインを有効化

→ 詳細は Vault 内の「運用ガイド/はじめに(セットアップ)」参照

### 変換する人(管理者)

```bash
bash tools/setup.sh              # 初回のみ(Homebrew 必須)
# OneNote からエクスポートした .one/.onepkg/.docx を input/ に置く
python3 tools/convert.py         # 変換実行(通達ノートも自動生成)
python3 tools/convert.py --push  # 変換して commit & push まで実行
```

→ 詳細は Vault 内の「運用ガイド/OneNoteからの変換手順」参照

## 同梱プラグイン

| プラグイン | 役割 |
| --- | --- |
| Dataview | ポータルの新着・通達・カテゴリ一覧の自動集計 |
| Obsidian Git | チーム同期(自動 pull / Commit-and-sync) |
| Omnisearch | 高精度な全文検索 |
| Homepage | 起動時に Home(ポータル)を自動表示 |
| Recent Files | 最近開いたファイルの一覧 |

## 動作環境

- 変換ツール: macOS (Apple Silicon) + Homebrew / Python 3.9+
- 閲覧: Obsidian デスクトップ版(Mac / Windows)。Git 同期はデスクトップ版のみ対応
