load("@rules_java//java:defs.bzl", "java_test")

common_deps_files = [
    "//third_party/java:mockito",
    "//third_party/java:junit4",
]

dlog_test_deps_files = \
    common_deps_files + [
        "@maven//:com_google_guava_guava",
        "//third_party/java:dlog-java",
        "@maven//:io_netty_netty_all",
        "@maven//:org_slf4j_log4j_over_slf4j",
        "//heron/io/dlog/src/java:dlog-lib",
    ]

java_test(
    name = "DLInputStreamTest",
    size = "small",
    srcs = glob(["**/dlog/DLInputStreamTest.java"]),
    deps = dlog_test_deps_files,
)

java_test(
    name = "DLOutputStreamTest",
    size = "small",
    srcs = glob(["**/dlog/DLOutputStreamTest.java"]),
    deps = dlog_test_deps_files,
)
