#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneNote → Obsidian Markdown 変換ツール

input/ に置いたファイルを vault/マニュアル/ 配下の Markdown に変換します。

対応形式:
  .one / .onetoc2  … one2html で HTML 化 → pandoc で Markdown 化
  .onepkg          … cabextract で展開 → 内部の .one を変換
  .docx            … pandoc で直接 Markdown 化 (OneNote の Word エクスポート用フォールバック)
  .html / .htm     … pandoc で直接 Markdown 化 (手動エクスポート用)

変換後:
  - YAML frontmatter (title / category / status / created / updated / source) を付与
  - 画像・添付ファイルは vault/添付ファイル/<ページ名>/ に集約し、リンクを書き換え
  - 新規・更新があった場合は vault/通達/ に通達ノートを自動生成

使い方:
  python3 tools/convert.py                       # input/ 内の全ファイルを変換
  python3 tools/convert.py path/to/section.one   # 個別ファイルを指定
  python3 tools/convert.py --category 経理部     # 出力先カテゴリ(フォルダ)を指定
  python3 tools/convert.py --push                # 変換後に git commit & push
  python3 tools/convert.py --dry-run             # 書き込みせずに結果だけ表示
"""
import argparse
import base64
import datetime
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ONE2HTML = REPO_ROOT / "tools" / "bin" / "one2html"
VAULT = REPO_ROOT / "vault"
MANUAL_DIR = VAULT / "マニュアル"
ATTACH_DIR = VAULT / "添付ファイル"
ANNOUNCE_DIR = VAULT / "通達"
INPUT_DIR = REPO_ROOT / "input"

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff"}

TODAY = datetime.date.today().isoformat()
NOW = datetime.datetime.now()


def sanitize(name: str) -> str:
    """Obsidian / ファイルシステムで問題になる文字を除去したファイル名を返す"""
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "無題"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=False, **kw)


def need(tool: str, hint: str):
    if shutil.which(tool) is None:
        sys.exit(f"ERROR: {tool} が見つかりません。{hint}")


# ---------------------------------------------------------------- 収集

def collect_html_jobs(src: Path, tmp: Path, category: str):
    """入力ファイル1つを HTML 群に展開し、(html_path, base_dir, group) のリストを返す。
    group は vault/マニュアル/ 配下の出力サブフォルダ。"""
    ext = src.suffix.lower()
    jobs = []

    if ext in (".one", ".onetoc2"):
        if not ONE2HTML.exists():
            sys.exit("ERROR: tools/bin/one2html がありません。先に `bash tools/setup.sh` を実行してください。")
        out = tmp / ("one_" + hashlib.md5(str(src).encode()).hexdigest()[:8])
        out.mkdir(parents=True, exist_ok=True)
        try:
            run([str(ONE2HTML), "--input", str(src), "--output", str(out)])
        except subprocess.CalledProcessError as e:
            print(f"  !! one2html が失敗しました: {src.name}")
            print("     " + e.stderr.decode("utf-8", "replace").strip().splitlines()[-1] if e.stderr else "")
            print("     → OneNote から Word(.docx) 形式でエクスポートし、input/ に置いて再実行するフォールバックが使えます。")
            return []
        group = category or sanitize(src.stem)
        for html in sorted(out.rglob("*.html")):
            jobs.append((html, html.parent, group))

    elif ext == ".onepkg":
        need("cabextract", "`brew install cabextract` を実行してください。")
        pkg_dir = tmp / ("pkg_" + hashlib.md5(str(src).encode()).hexdigest()[:8])
        pkg_dir.mkdir(parents=True, exist_ok=True)
        run(["cabextract", "-q", "-d", str(pkg_dir), str(src)])
        ones = sorted(pkg_dir.rglob("*.one"))
        if not ones:
            print(f"  !! .onepkg 内に .one が見つかりません: {src.name}")
            return []
        book = category or sanitize(src.stem)
        for one in ones:
            for html, base, _ in collect_html_jobs(one, tmp, ""):
                jobs.append((html, base, f"{book}/{sanitize(one.stem)}"))

    elif ext == ".docx":
        jobs.append((src, src.parent, category or sanitize(src.stem)))

    elif ext in (".html", ".htm"):
        jobs.append((src, src.parent, category or sanitize(src.stem)))

    else:
        print(f"  -- 未対応の形式のためスキップ: {src.name}")

    return jobs


# ---------------------------------------------------------------- 変換

def to_markdown(path: Path, media_dir: Path) -> str:
    """pandoc で Markdown (GFM) に変換して返す"""
    fmt = "docx" if path.suffix.lower() == ".docx" else "html"
    cmd = ["pandoc", "-f", fmt, "-t", "gfm-raw_html", "--wrap=none"]
    if fmt == "docx":
        cmd += ["--extract-media", str(media_dir)]
    cmd.append(str(path))
    res = run(cmd)
    return res.stdout.decode("utf-8", "replace")


def html_title(path: Path) -> str:
    if path.suffix.lower() in (".html", ".htm"):
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
        if m and m.group(1).strip():
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            return sanitize(t)
    return sanitize(path.stem)


def rewrite_media(md: str, base_dir: Path, slug: str, dry: bool) -> str:
    """Markdown 内の画像・ファイルリンクを vault/添付ファイル/<slug>/ に集約し、
    Obsidian の wikilink 形式に書き換える"""
    dest_dir = ATTACH_DIR / slug
    counter = {"n": 0}

    def save_bytes(data: bytes, suggested: str) -> str:
        counter["n"] += 1
        fname = f"{slug}_{counter['n']:02d}_{sanitize(suggested)}"
        if not dry:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / fname).write_bytes(data)
        return fname

    def save_file(fp: Path) -> str:
        counter["n"] += 1
        fname = f"{slug}_{counter['n']:02d}_{sanitize(fp.name)}"
        if not dry:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, dest_dir / fname)
        return fname

    def resolve(src: str):
        src = src.strip()
        if src.startswith("data:"):
            m = re.match(r"data:image/(\w+);base64,(.*)", src, re.S)
            if m:
                try:
                    return save_bytes(base64.b64decode(m.group(2)), f"image.{m.group(1)}")
                except Exception:
                    return None
            return None
        if re.match(r"^[a-z]+://", src):  # 外部URLはそのまま
            return None
        p = Path(urllib.parse.unquote(src))
        fp = p if p.is_absolute() else (base_dir / p)
        if fp.exists() and fp.is_file():
            return save_file(fp)
        return None

    def img_repl(m):
        name = resolve(m.group(2))
        return f"![[{name}]]" if name else m.group(0)

    def link_repl(m):
        label, src = m.group(1), m.group(2)
        if re.match(r"^[a-z]+://", src.strip()) or src.startswith("#"):
            return m.group(0)
        name = resolve(src)
        return f"[[{name}|{label or name}]]" if name else m.group(0)

    md = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", img_repl, md)
    md = re.sub(r"(?<!\!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", link_repl, md)
    return md


# ---------------------------------------------------------------- 出力

def read_frontmatter(path: Path):
    """既存ファイルの (frontmatter dict, body) を返す"""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip()
    return fm, text[m.end():]


def write_page(title: str, group: str, body: str, source: str, dry: bool) -> str:
    """ページを書き込み、'new' / 'updated' / 'unchanged' を返す"""
    out_dir = MANUAL_DIR / group
    out_path = out_dir / f"{title}.md"
    body = body.strip() + "\n"
    body_hash = hashlib.sha256(body.encode()).hexdigest()

    created, prev_hash = TODAY, None
    if out_path.exists():
        fm, prev_body = read_frontmatter(out_path)
        created = fm.get("created", TODAY)
        prev_hash = hashlib.sha256(prev_body.strip().encode()).hexdigest()
        if prev_hash == hashlib.sha256(body.strip().encode()).hexdigest():
            return "unchanged"
        updated = TODAY
        status = "updated"
    else:
        updated = TODAY
        status = "new"

    fm_text = (
        "---\n"
        f"title: {title}\n"
        f"category: {group}\n"
        "tags:\n  - マニュアル\n"
        "status: 公開\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"source: {source}\n"
        "---\n\n"
    )
    if not dry:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(fm_text + body, encoding="utf-8")
    return status


def write_announcement(new_pages, updated_pages, dry: bool):
    stamp = NOW.strftime("%Y-%m-%d %H%M")
    path = ANNOUNCE_DIR / f"{stamp} マニュアル更新のお知らせ.md"
    lines = [
        "---",
        f"title: {stamp} マニュアル更新のお知らせ",
        "tags:\n  - 通達",
        f"date: {TODAY}",
        "type: 自動生成",
        "---",
        "",
        f"> [!info] OneNote からの変換により、マニュアルが追加・更新されました({NOW.strftime('%Y-%m-%d %H:%M')})。",
        "",
    ]
    if new_pages:
        lines.append("## 🆕 新規マニュアル")
        lines += [f"- [[{t}]] ({g})" for t, g in new_pages]
        lines.append("")
    if updated_pages:
        lines.append("## 🔄 更新されたマニュアル")
        lines += [f"- [[{t}]] ({g})" for t, g in updated_pages]
        lines.append("")
    if not dry:
        ANNOUNCE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
    return path


def git_push(message: str):
    subprocess.run(["git", "-C", str(REPO_ROOT), "add", "vault"], check=True)
    diff = subprocess.run(["git", "-C", str(REPO_ROOT), "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("git: コミットする変更はありません。")
        return
    subprocess.run(["git", "-C", str(REPO_ROOT), "commit", "-m", message], check=True)
    subprocess.run(["git", "-C", str(REPO_ROOT), "push"], check=True)
    print("git: push 完了。チームメンバーには Obsidian Git の自動 pull で共有されます。")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="OneNote → Obsidian Markdown 変換")
    ap.add_argument("inputs", nargs="*", help="変換するファイル(省略時は input/ 内の全ファイル)")
    ap.add_argument("--category", default="", help="出力先カテゴリ(vault/マニュアル/ 配下のフォルダ名)")
    ap.add_argument("--no-announce", action="store_true", help="通達ノートを生成しない")
    ap.add_argument("--push", action="store_true", help="変換後に git commit & push する")
    ap.add_argument("--dry-run", action="store_true", help="書き込みせずに結果のみ表示")
    args = ap.parse_args()

    need("pandoc", "`brew install pandoc` を実行してください。")

    if args.inputs:
        sources = [Path(p).resolve() for p in args.inputs]
    else:
        sources = sorted(
            p for p in INPUT_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in (".one", ".onetoc2", ".onepkg", ".docx", ".html", ".htm")
        ) if INPUT_DIR.exists() else []

    if not sources:
        sys.exit("変換対象がありません。input/ に .one / .onepkg / .docx ファイルを置いて再実行してください。")

    new_pages, updated_pages, unchanged = [], [], 0

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        for src in sources:
            if not src.exists():
                print(f"  !! ファイルが見つかりません: {src}")
                continue
            print(f"==> {src.name}")
            for doc, base_dir, group in collect_html_jobs(src, tmp, args.category):
                title = html_title(doc)
                slug = sanitize(f"{group.replace('/', '_')}_{title}")[:80]
                md = to_markdown(doc, tmp / "media" / slug)
                md = rewrite_media(md, base_dir, slug, args.dry_run)
                # docx の --extract-media で出た画像も回収
                md = rewrite_media(md, tmp, slug, args.dry_run)
                status = write_page(title, group, md, f"OneNote:{src.name}", args.dry_run)
                mark = {"new": "🆕 新規", "updated": "🔄 更新", "unchanged": "-- 変更なし"}[status]
                print(f"    {mark}: マニュアル/{group}/{title}.md")
                if status == "new":
                    new_pages.append((title, group))
                elif status == "updated":
                    updated_pages.append((title, group))
                else:
                    unchanged += 1

    print()
    print(f"完了: 新規 {len(new_pages)} 件 / 更新 {len(updated_pages)} 件 / 変更なし {unchanged} 件")

    if (new_pages or updated_pages) and not args.no_announce:
        path = write_announcement(new_pages, updated_pages, args.dry_run)
        print(f"通達ノートを作成しました: {path.relative_to(REPO_ROOT)}")

    if args.push and not args.dry_run:
        git_push(f"マニュアル変換: 新規{len(new_pages)}件 更新{len(updated_pages)}件")


if __name__ == "__main__":
    main()
