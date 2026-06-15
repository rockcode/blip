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

err() { echo "错误: $*" >&2; exit 1; }

cd "$(dirname "$0")"

[[ -n "$VERSION" ]] || err "用法: ./release.sh <version>   (例: ./release.sh 1.1.0)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || err "版本号需形如 1.2.3，收到: $VERSION"
[[ "$(git branch --show-current)" == "main" ]] || err "请切到 main 分支再发布"
[[ -z "$(git status --porcelain)" ]] || err "工作树有未提交改动，请先提交或清理"
! git rev-parse "v$VERSION" >/dev/null 2>&1 || err "tag v$VERSION 已存在"
grep -q "^## v$VERSION" CHANGELOG.md || err "CHANGELOG.md 缺少 '## v$VERSION …' 段落，请先写好发布说明"

# 从 CHANGELOG 取该版本的发布说明(到下一个 ## 标题之前)
NOTES="$(awk -v v="^## v$VERSION" '$0 ~ v {f=1; next} f && /^## / {exit} f {print}' CHANGELOG.md)"

echo "== 即将发布 blip v$VERSION，发布说明如下 =="
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

# 提交 + tag + 推送 + 发布
git add "$INIT"
git commit -q -m "chore: release v$VERSION"
git push -q origin main
git tag -a "v$VERSION" -m "blip v$VERSION"
git push -q origin "v$VERSION"
gh release create "v$VERSION" --title "blip v$VERSION" --notes "$NOTES"

echo "✅ 已发布 blip v$VERSION"
