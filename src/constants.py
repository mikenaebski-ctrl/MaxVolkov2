"""Named constants shared across the tool."""

PARAM_PACKAGE = "package_name"
PARAM_REPO_URL = "repository_url"
PARAM_REPO_MODE = "repository_mode"
PARAM_VERSION = "package_version"
PARAM_OUTPUT = "output_image"
PARAM_ASCII = "ascii_tree"
PARAM_DEPTH = "max_depth"
PARAMETERS = (
    PARAM_PACKAGE,
    PARAM_REPO_URL,
    PARAM_REPO_MODE,
    PARAM_VERSION,
    PARAM_OUTPUT,
    PARAM_ASCII,
    PARAM_DEPTH,
)

CSV_HEADER = ("parameter", "value")
ENCODING = "utf-8-sig"
DEFAULT_CONFIG = "config.csv"

MODE_REAL = "real"
MODE_TEST = "test"
MODES = (MODE_REAL, MODE_TEST)

TRUE_WORDS = ("true", "yes", "on")
FALSE_WORDS = ("false", "no", "off")
URL_SCHEMES = ("http", "https", "file")
WEB_SCHEMES = ("http", "https")
IMAGE_SUFFIX = ".png"
MIN_DEPTH = 1

MAVEN_NAME_PATTERN = r"^[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-]+$"
TEST_NAME_PATTERN = r"^[A-Z]+$"
VERSION_PATTERN = r"^[0-9A-Za-z][0-9A-Za-z_.+\-]*$"
DEPTH_PATTERN = r"^[0-9]+$"

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USER_ERROR = 2

HTTP_TIMEOUT = 20
HTTP_NOT_FOUND = 404
USER_AGENT = "maven-dependency-graph/1.0"
POM_ROOT_TAG = "project"
SCOPE_COMPILE = "compile"
SCOPE_RUNTIME = "runtime"
SCOPE_IMPORT = "import"
INCLUDED_SCOPES = (SCOPE_COMPILE, SCOPE_RUNTIME)
MAX_PARENT_DEPTH = 20
MAX_INTERPOLATION_PASSES = 10
TEST_REPO_LINE = r"^([A-Z]+)\s*:\s*([A-Z\s]*)$"
