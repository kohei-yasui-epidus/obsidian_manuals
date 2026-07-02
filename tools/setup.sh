#!/usr/bin/env bash
# =============================================================
# 変換環境セットアップスクリプト (macOS)
#   - pandoc      : HTML/docx → Markdown 変換
#   - cabextract  : .onepkg (CAB形式) の展開
#   - one2html    : .one / .onetoc2 → HTML 変換 (GitHub Releases)
# 使い方: bash tools/setup.sh
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
ONE2HTML_VERSION="v1.3.1"

if ! command -v brew >/dev/null 2>&1; then
  echo "ERROR: Homebrew が見つかりません。https://brew.sh を参照してインストールしてください。" >&2
  exit 1
fi

echo "==> pandoc / cabextract を確認・インストールします"
command -v pandoc >/dev/null 2>&1 || brew install pandoc
command -v cabextract >/dev/null 2>&1 || brew install cabextract

echo "==> one2html ($ONE2HTML_VERSION) をダウンロードします"
mkdir -p "$BIN_DIR"
if [ ! -x "$BIN_DIR/one2html" ]; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    arm64)  ASSET="one2html-aarch64-apple-darwin.tar.gz" ;;
    x86_64) echo "ERROR: x86_64 Mac 用のビルド済みバイナリは提供されていません。'cargo install one2html' を利用してください。" >&2; exit 1 ;;
    *)      echo "ERROR: 未対応のアーキテクチャ: $ARCH" >&2; exit 1 ;;
  esac
  curl -sL "https://github.com/msiemens/one2html/releases/download/$ONE2HTML_VERSION/$ASSET" \
    | tar xz -C "$BIN_DIR"
  chmod +x "$BIN_DIR/one2html"
fi

echo ""
echo "セットアップ完了。以下で動作確認できます:"
echo "  pandoc --version | head -1"
echo "  $BIN_DIR/one2html --help"
echo ""
echo "変換の実行:"
echo "  python3 tools/convert.py"
