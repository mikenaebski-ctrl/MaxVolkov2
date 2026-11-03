# Maven dependency graph visualizer (variant 6)

Practical work for "Configuration Management", RTU MIREA.
The tool builds and draws the dependency graph of a Maven package.

Done so far: stage 1 (CSV configuration), stage 2 (direct dependencies
read from POM files without any package manager) and stage 3 (the whole
graph built with BFS, depth limit, cycles, test repository files) and
stage 4 (the order of loading the dependencies).

```sh
sh run.sh --show-config            # stage 1: print the parameters
sh run.sh --direct                 # stage 2: print direct dependencies
sh run.sh                          # stage 3: build and print the graph
sh run.sh --load-order             # stage 4: dependencies first
sh run.sh --config examples/config_test_cycle.csv
sh scripts/compare_with_mvn.sh org.slf4j:slf4j-simple:2.0.9
```

## Load order (stage 4)

`--load-order` prints the packages so that every package comes after
all of its dependencies (an iterative post-order walk over the graph;
the edge that closes a cycle is ignored).

`scripts/compare_with_mvn.sh GROUP:ARTIFACT:VERSION` runs the real
`mvn dependency:tree` and this tool for the same package and shows both
lists plus the packages found by only one of them.

Why the results may differ from Maven:

- Maven lists the tree in pre-order (a package before its dependencies)
  and builds the class path in that order; this tool lists dependencies
  first, which is the order they must be available when loading.
- Maven resolves version conflicts with "nearest wins"; this tool does
  the same with BFS, but exclusions, `optional` details of the whole
  tree and Maven plugins settings are not modelled.
- Only compile and runtime scopes are followed here, as in
  `-Dscope=runtime`.
- Version ranges are replaced by their lower bound.
