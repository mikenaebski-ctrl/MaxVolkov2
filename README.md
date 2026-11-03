# Maven dependency graph visualizer (variant 6)

Practical work for "Configuration Management", RTU MIREA.
The tool builds and draws the dependency graph of a Maven package.

Done so far: stage 1 (CSV configuration), stage 2 (direct dependencies
read from POM files without any package manager) and stage 3 (the whole
graph built with BFS, depth limit, cycles, test repository files).

```sh
sh run.sh --show-config            # stage 1: print the parameters
sh run.sh --direct                 # stage 2: print direct dependencies
sh run.sh                          # stage 3: build and print the graph
sh run.sh --config examples/config_test_cycle.csv
```
