#!/bin/sh
# Compare the load order of this tool with the real Maven for one package.
# Usage: scripts/compare_with_mvn.sh GROUP:ARTIFACT:VERSION [MAX_DEPTH]
# Needs: mvn, python3 and access to the repository (MAVEN_REPO_URL).
set -eu

if [ $# -lt 1 ]; then
    echo "usage: $0 GROUP:ARTIFACT:VERSION [MAX_DEPTH]" >&2
    exit 2
fi
if ! command -v mvn >/dev/null 2>&1; then
    echo "error: mvn is not installed, nothing to compare with" >&2
    exit 1
fi

root_dir=$(cd "$(dirname "$0")/.." && pwd)
coords=$1
depth=${2:-50}
repo=${MAVEN_REPO_URL:-https://repo.maven.apache.org/maven2}
group=${coords%%:*}
rest=${coords#*:}
artifact=${rest%%:*}
version=${rest#*:}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

cat > "$work/pom.xml" <<POM
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>compare</groupId>
  <artifactId>probe</artifactId>
  <version>1</version>
  <dependencies>
    <dependency>
      <groupId>$group</groupId>
      <artifactId>$artifact</artifactId>
      <version>$version</version>
    </dependency>
  </dependencies>
</project>
POM

cat > "$work/config.csv" <<CSV
parameter,value
package_name,$group:$artifact
repository_url,$repo
repository_mode,real
package_version,$version
output_image,compare.png
ascii_tree,false
max_depth,$depth
CSV

(cd "$work" && mvn -q -B dependency:tree -Dscope=runtime \
    -DoutputFile="$work/tree.txt")
awk '{ n = split($NF, p, ":"); print p[1] ":" p[2] ":" p[n - 1 + (n == 4)] }' \
    "$work/tree.txt" | sed '1d' > "$work/maven.txt"
(cd "$root_dir" && python3 -B -m src --config "$work/config.csv" \
    --load-order > "$work/order.txt")
sed -n 's/^ *[0-9]*\. //p' "$work/order.txt" > "$work/ours.txt"

echo "== Maven (dependency:tree, pre-order, without the probe project)"
cat "$work/maven.txt"
echo "== This tool (--load-order, dependencies first)"
cat "$work/ours.txt"
sort "$work/maven.txt" > "$work/maven.sorted"
sort "$work/ours.txt" > "$work/ours.sorted"
echo "== Only in Maven"
comm -23 "$work/maven.sorted" "$work/ours.sorted"
echo "== Only in this tool"
comm -13 "$work/maven.sorted" "$work/ours.sorted"
