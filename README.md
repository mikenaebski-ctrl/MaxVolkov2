# Maven dependency graph visualizer (variant 6)

Practical work no. 2 for "Configuration Management", RTU MIREA.

The tool reads the POM files of a Maven package, builds the graph of its
transitive dependencies and shows it as an ASCII tree, as a dependency
load order, as PlantUML text and as a PNG image. It needs only Python 3.9+
and its standard library; no package manager or third-party library is
used to get the dependencies (POM files are downloaded with `urllib` and
parsed with `xml.etree`).

## Features

- CSV configuration with checks of every parameter (stage 1).
- Direct dependencies of a package read from its POM, including
  properties, parent POMs, `dependencyManagement`, BOM imports and version
  ranges (stage 2).
- Graph built by breadth-first search without recursion, with a depth
  limit, cycle detection and a test repository mode (stage 3).
- Load order of the dependencies, dependencies first (stage 4).
- PlantUML text, PNG image and ASCII tree (stage 5).

## Configuration

`config.csv` has the header `parameter,value` and one row per parameter:

| parameter         | meaning                                              |
|-------------------|------------------------------------------------------|
| `package_name`    | `groupId:artifactId` (real mode) or `A`..`Z` (test)  |
| `repository_url`  | Maven repository URL, or path of the test repo file  |
| `repository_mode` | `real` or `test`                                     |
| `package_version` | package version                                      |
| `output_image`    | name of the PNG file                                 |
| `ascii_tree`      | `true` or `false`: print the ASCII tree              |
| `max_depth`       | maximum depth of the graph (1 or more)               |

All wrong parameters are reported at once; the exit code is 2 for a bad
configuration and 1 for other errors (package not found, network, render).

A test repository is a text file with one line per package, for example
`A: B C`. Package names are capital Latin letters, `#` starts a comment.

## Commands

```sh
sh run.sh --show-config            # stage 1: print the parameters
sh run.sh --direct                 # stage 2: direct dependencies
sh run.sh                          # stage 3: graph, ASCII tree, summary
sh run.sh --load-order             # stage 4: dependencies first
sh run.sh --plantuml               # stage 5: PlantUML text
sh run.sh --plantuml-jar plantuml.jar          # stage 5: PNG with a jar
sh run.sh --plantuml-server https://www.plantuml.com/plantuml
sh run.sh --config examples/config_test_cycle.csv
sh scripts/demo.sh                 # show all stages
```

On Windows use `run.bat` instead of `sh run.sh`; `make run`, `make test`
and `make demo` do the same with make.

`--plantuml-jar` runs `java -jar FILE -pipe -tpng`; `--plantuml-server`
sends the encoded text to a PlantUML server. Both write the PNG to
`output_image` and the PlantUML source next to it (`.puml`). PNG and
`.puml` files are not stored in git (see `.gitignore`).

## Build and tests

No build step is needed. Run the tests (they include style checks of the
source code: line length, function size, complexity, docstrings):

```sh
python3 -B -m unittest discover -s tests -t .
```

## Examples

Test repository `examples/test_repo_basic.txt` with `max_depth` 3:

```text
A
├── B
│   └── D
│       └── F
└── C
    ├── D (*)
    └── E
        └── F
Packages: 6, dependencies: 7, cycles: 0, depth limit: 3
```

`(*)` means the dependencies of the package are already shown above and
`(cycle)` means that the package is its own ancestor. Ready PlantUML
texts are in `examples/graph_*.puml`. Real packages:
`examples/config_real_slf4j.csv`, `config_real_jackson.csv` and
`config_real_guava.csv`.

## Load order and the comparison with Maven

`--load-order` is an iterative post-order walk: a package is printed after
all of its dependencies, an edge that closes a cycle is ignored.
`scripts/compare_with_mvn.sh GROUP:ARTIFACT:VERSION` runs
`mvn dependency:tree` and this tool for the same package and prints both
lists and the packages that only one of them contains.

Why the results may differ from real Maven:

- Maven prints the tree in pre-order (a package before its dependencies);
  this tool prints dependencies first.
- Maven mediates versions with "nearest wins" for the whole project; here
  BFS keeps the first version found, the other one is reported.
- `exclusions`, profiles, `optional` dependencies of dependencies and
  plugin settings are only partly modelled. Only `compile` and `runtime`
  scopes are followed. A version range is replaced by its lower bound.

## Comparison with the visualization tools of Maven

| tool | what it gives | difference from this tool |
|------|---------------|---------------------------|
| `mvn dependency:tree` | text tree of a project; `-Dverbose` shows omitted duplicates and conflicts; `-DoutputType=dot`, `graphml`, `tgf` | needs Maven and a project; resolves exclusions, profiles and scopes exactly; the result is always a tree |
| depgraph-maven-plugin and IDE views | PNG or interactive graph via Graphviz or the IDE | needs a plugin or an IDE; richer styling; no cycles to show after mediation |
| this tool | ASCII tree, load order, PlantUML text and PNG for one coordinate | no Maven or project needed; shows cycles and repeated packages; simpler model of Maven rules |

## Project layout

```text
src/        source code (config, pom, maven_repo, graph, order, plantuml)
tests/      unit tests and code style checks
examples/   configurations, test repositories, PlantUML texts
scripts/    demo.sh and compare_with_mvn.sh
run.sh run.bat Makefile    start scripts
```
