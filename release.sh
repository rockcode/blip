#!/usr/bin/env bash
#
# 发布新版本。用法:  ./release.sh <version>      例如  ./release.sh 1.1.0
#
# 前置：先在 CHANGELOG.md 顶部写好  "## v<version> — <日期>"  段落(作为发布说明)。
# 脚本会：校验 -> 改 __version__ -> 跑测试 -> 提交 -> 打 tag -> 推送 -> 建 GitHub Release。
#
set -euo pipefail

VERSION="${1:-}"
INIT="blipmon/__init__.py"
PYZ="blip.pyz"

err() { echo "错误: $*" >&2; exit 1; }

# 把 blipmon 包打成单文件 blip.pyz(零依赖、跨平台，需对方装 Python 3.11+)
build_pyz() {
    rm -rf build_pyz "$PYZ"
    mkdir build_pyz
    cp -R blipmon build_pyz/
    find build_pyz -name __pycache__ -type d -exec rm -rf {} +
    python3 -m zipapp build_pyz -m "blipmon.app:main" \
        -p "/usr/bin/env python3" -o "$PYZ"
    rm -rf build_pyz
    chmod +x "$PYZ"
    "./$PYZ" --version >/dev/null || err "构建出的 $PYZ 无法运行"
    cp "$PYZ" plugin/blip.pyz       # 同步插件内捆绑的单文件(随仓库提交)
}

cd "$(dirname "$0")"

[[ -n "$VERSION" ]] || err "用法: ./release.sh <version>   (例: ./release.sh 1.1.0)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || err "版本号需形如 1.2.3，收到: $VERSION"
[[ "$(git branch --show-current)" == "main" ]] || err "请切到 main 分支再发布"
[[ -z "$(git status --porcelain)" ]] || err "工作树有未提交改动，请先提交或清理"
! git rev-parse "v$VERSION" >/dev/null 2>&1 || err "tag v$VERSION 已存在"
grep -q "^## v$VERSION" CHANGELOG.md || err "CHANGELOG.md 缺少 '## v$VERSION …' 段落，请先写好发布说明"

# 从 CHANGELOG 取该版本的发布说明(到下一个 ## 标题之前)
NOTES="$(awk -v v="^## v$VERSION" '$0 ~ v {f=1; next} f && /^## / {exit} f {print}' CHANGELOG.md)"

echo "== 即将发布 blip v${VERSION}，发布说明如下 =="
echo "$NOTES"
echo "==========================================="
read -r -p "确认发布? [y/N] " ans
[[ "$ans" == "y" || "$ans" == "Y" ]] || err "已取消"

# 改版本号
sed -i '' -E "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" "$INIT"
grep -q "__version__ = \"$VERSION\"" "$INIT" || err "写入 $INIT 失败"

# 测试闸门(失败则撤销改动)
echo "== 跑测试 =="
if ! python3 -m unittest discover -s tests >/dev/null 2>&1; then
    git checkout -- "$INIT"
    err "测试未通过，已撤销版本号改动并中止发布"
fi

# 构建单文件产物(失败则撤销版本号改动并中止)
echo "== 构建 $PYZ =="
if ! build_pyz; then
    git checkout -- "$INIT"
    err "构建 $PYZ 失败，已撤销版本号改动并中止发布"
fi

# 提交 + tag + 推送 + 发布(blip.pyz 作为 Release 附件，供人直接下载运行)
git add "$INIT" plugin/blip.pyz
git commit -q -m "chore: release v$VERSION"
git push -q origin main
git tag -a "v$VERSION" -m "blip v$VERSION"
git push -q origin "v$VERSION"
gh release create "v$VERSION" --title "blip v$VERSION" --notes "$NOTES" "$PYZ"
rm -f "$PYZ"

echo "✅ 已发布 blip v${VERSION}（含单文件 $PYZ 附件）"
