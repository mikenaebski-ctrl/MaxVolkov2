#!/bin/sh
# Show every stage. Optional: PLANTUML_JAR=/path/plantuml.jar renders PNGs.
set -eu
cd "$(dirname "$0")/.."

run() {
    echo "\$ sh run.sh $*"
    sh run.sh "$@"
    echo
}

run --show-config
run --direct
run
run --load-order
run --config examples/config_test_cycle.csv
run --config examples/config_test_chain.csv
run --plantuml --config examples/config_test_cycle.csv

if [ -n "${PLANTUML_JAR:-}" ]; then
    run --plantuml-jar "$PLANTUML_JAR"
fi

for name in slf4j jackson guava; do
    echo "Real package example: examples/config_real_$name.csv"
    echo "  sh run.sh --config examples/config_real_$name.csv"
done
