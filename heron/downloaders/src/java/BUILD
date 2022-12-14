load("@rules_java//java:defs.bzl", "java_binary", "java_library")

licenses(["notice"])

package(default_visibility = ["//visibility:public"])

files = glob(
    ["**/*.java"],
    exclude = ["**/DownloadRunner.java"],
)

downloader_deps = [
    "//heron/io/dlog/src/java:dlog-lib",
    "//heron/api/src/java:api-java-low-level",
    "//heron/spi/src/java:common-spi-java",
    "//third_party/java:commons-compress",
    "@maven//:commons_cli_commons_cli",
    "//third_party/java:dlog-java",
    "@maven//:io_netty_netty_all",
]

java_library(
    name = "downloader-java",
    srcs = files,
    deps = downloader_deps,
)

filegroup(
    name = "downloader-main",
    srcs = glob(["**/DownloadRunner.java"]),
)

filegroup(
    name = "downloader-core",
    srcs = glob([
        "**/Downloader.java",
        "**/Extractor.java",
        "**/Registry.java",
    ]),
)

java_binary(
    name = "heron-downloader-unshaded",
    srcs = [":downloader-main"],
    main_class = "org.apache.heron.downloader.DownloadRunner",
    deps = downloader_deps + [":downloader-java"],
)

genrule(
    name = "heron-downloader",
    srcs = [":heron-downloader-unshaded_deploy.jar"],
    outs = ["heron-downloader.jar"],
    cmd = "cp $< $@",
)
