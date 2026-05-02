#!/usr/bin/env python3
"""Trace direct method calls made by a Java class method.

A small Java source index resolves receiver variables to project classes and
recurses into local project methods when requested. The default matcher is a
fast deterministic parser. Pass `--engine semgrep` to use Semgrep for
receiver-qualified call matching and the parser for constructors/local calls.

Semgrep OSS taint mode is intraprocedural, so this script uses Semgrep as a
deterministic method-body matcher rather than pretending to compute a full
interprocedural taint graph.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict, deque


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JAVA_ROOTS = [
    os.path.join(REPO_ROOT, "daytrader3-ee6-web", "src", "main", "java"),
    os.path.join(REPO_ROOT, "daytrader3-ee6-ejb", "src", "main", "java"),
    os.path.join(REPO_ROOT, "daytrader3-ee6-rest", "src", "main", "java"),
]
SEMGREP_BIN = os.path.join(REPO_ROOT, ".venv", "bin", "semgrep")

PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+([\w.*]+)\s*;", re.MULTILINE)
CLASS_RE = re.compile(
    r"^\s*(?:public|protected|private)?\s*(?:abstract\s+|final\s+)?"
    r"(?:class|interface)\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([^{]+))?",
    re.MULTILINE,
)
TYPE_NAME_RE = re.compile(r"[A-Z]\w*(?:\s*<[^;=(){}]+>)?(?:\s*\[\s*\])?")
DECL_RE = re.compile(
    r"(?:^|[;{}\n])\s*(?:public|protected|private)?\s*(?:static\s+)?(?:final\s+)?"
    r"([A-Z]\w*(?:\s*<[^;=(){}]+>)?(?:\s*\[\s*\])?)\s+(\w+)\s*(?:=|;|,)"
)
METHOD_HEADER_RE = re.compile(
    r"(?:@\w+(?:\([^)]*\))?\s*)*"
    r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?"
    r"([\w.$<>?,\s\[\]]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\{",
    re.MULTILINE,
)


EXTERNAL_TYPES = {
    "String",
    "Integer",
    "Long",
    "Double",
    "Float",
    "Boolean",
    "BigDecimal",
    "Collection",
    "Iterator",
    "List",
    "Map",
    "Set",
    "Connection",
    "PreparedStatement",
    "ResultSet",
}

LOCAL_CALL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "throw",
    "throws",
    "new",
    "synchronized",
    "assert",
    "super",
}


def normalize_type(type_name):
    if not type_name:
        return None
    type_name = re.sub(r"<.*>", "", type_name)
    type_name = type_name.replace("[]", "")
    return type_name.strip().split(".")[-1]


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def line_for_offset(text, offset):
    return text.count("\n", 0, offset) + 1


def brace_end(text, open_brace):
    depth = 0
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    for i in range(open_brace, len(text)):
        c = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue
        if in_char:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == "'":
                in_char = False
            continue

        if c == "/" and nxt == "/":
            in_line_comment = True
            continue
        if c == "/" and nxt == "*":
            in_block_comment = True
            continue
        if c == '"':
            in_string = True
            continue
        if c == "'":
            in_char = True
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i

    return -1


def build_index():
    classes = {}
    implementors = defaultdict(list)
    methods = defaultdict(dict)

    for root in JAVA_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                path = os.path.join(dirpath, filename)
                text = read_text(path)
                class_match = CLASS_RE.search(text)
                if not class_match:
                    continue

                package_match = PACKAGE_RE.search(text)
                package = package_match.group(1) if package_match else ""
                simple = class_match.group(1)
                extends = normalize_type(class_match.group(2))
                implements = [
                    normalize_type(part.strip())
                    for part in (class_match.group(3) or "").split(",")
                    if part.strip()
                ]

                classes[simple] = {
                    "simple": simple,
                    "fqn": package + "." + simple if package else simple,
                    "path": path,
                    "text": text,
                    "imports": list(IMPORT_RE.findall(text)),
                    "extends": extends,
                    "implements": implements,
                }

                if extends:
                    implementors[extends].append(simple)
                for interface in implements:
                    implementors[interface].append(simple)

                for method_match in METHOD_HEADER_RE.finditer(text):
                    open_brace = text.find("{", method_match.start())
                    end = brace_end(text, open_brace)
                    if end == -1:
                        continue
                    method_name = method_match.group(2)
                    if method_name in methods[simple]:
                        continue
                    methods[simple][method_name] = {
                        "return_type": normalize_type(method_match.group(1)),
                        "params": method_match.group(3),
                        "start": method_match.start(),
                        "body_start": open_brace + 1,
                        "body_end": end,
                        "line": line_for_offset(text, method_match.start()),
                    }

    return classes, methods, implementors


def subtype_closure(type_name, implementors):
    seen = set()
    queue = deque(implementors.get(type_name, []))
    result = []
    while queue:
        child = queue.popleft()
        if child in seen:
            continue
        seen.add(child)
        result.append(child)
        queue.extend(implementors.get(child, []))
    return result


def resolve_class(name, classes):
    simple = normalize_type(name)
    if simple in classes:
        return simple
    for class_name, info in classes.items():
        if info["fqn"] == name:
            return class_name
    return None


def infer_types(class_name, method_name, classes, methods):
    info = classes[class_name]
    method = methods[class_name][method_name]
    text = info["text"]
    body = text[method["body_start"] : method["body_end"]]
    first_method_start = min(
        (data["start"] for data in methods.get(class_name, {}).values()),
        default=method["start"],
    )
    field_scope = text[:first_method_start]

    types = {"this": class_name}

    for raw_param in method["params"].split(","):
        raw_param = raw_param.strip()
        if not raw_param:
            continue
        raw_param = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", raw_param)
        parts = raw_param.split()
        if len(parts) >= 2:
            types[parts[-1].replace("...", "").strip()] = normalize_type(" ".join(parts[:-1]))

    for scope in (field_scope, body):
        for match in DECL_RE.finditer(scope):
            type_name = normalize_type(match.group(1))
            var_name = match.group(2)
            if type_name and type_name not in EXTERNAL_TYPES:
                types[var_name] = type_name

    for match in re.finditer(r"\b(\w+)\s*=\s*new\s+([A-Z]\w+)\s*\(", body):
        types[match.group(1)] = match.group(2)

    for match in re.finditer(r"\(([A-Z]\w+)\)\s*(\w+)", body):
        types[match.group(2)] = match.group(1)

    return types


def semgrep_command():
    if os.path.exists(SEMGREP_BIN):
        return SEMGREP_BIN
    return shutil.which("semgrep")


def run_semgrep(class_name, method_name, classes, timeout_seconds):
    semgrep = semgrep_command()
    if not semgrep:
        return None

    with tempfile.TemporaryDirectory(prefix="daytrader-semgrep-", dir="/tmp") as tmpdir:
        rule_path = os.path.join(tmpdir, "trace.yml")
        with open(rule_path, "w", encoding="utf-8") as f:
            f.write(
                """rules:
  - id: trace-object-calls
    languages: [java]
    severity: INFO
    message: object-call $OBJ.$CALL
    patterns:
      - pattern-inside: |
          $RET %s(...) {
            ...
          }
      - pattern: $OBJ.$CALL(...)
"""
                % method_name
            )

        env = os.environ.copy()
        env["HOME"] = "/tmp/semgrep-home"
        env["XDG_CONFIG_HOME"] = "/tmp/semgrep-config"
        os.makedirs(env["HOME"], exist_ok=True)
        os.makedirs(env["XDG_CONFIG_HOME"], exist_ok=True)

        cmd = [
            semgrep,
            "scan",
            "--quiet",
            "--metrics",
            "off",
            "--config",
            rule_path,
            "--json",
            classes[class_name]["path"],
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return None
        if proc.returncode not in (0, 1):
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
        return json.loads(proc.stdout or "{}").get("results", [])


def fallback_calls(class_name, method_name, classes, methods):
    method = methods[class_name][method_name]
    text = classes[class_name]["text"]
    body = text[method["body_start"] : method["body_end"]]
    base_line = line_for_offset(text, method["body_start"])
    calls = []

    for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(", body):
        calls.append(
            {
                "line": base_line + body.count("\n", 0, match.start()),
                "receiver": match.group(1),
                "method": match.group(2),
            }
        )

    return calls


def parser_extra_calls(class_name, method_name, classes, methods):
    method = methods[class_name][method_name]
    text = classes[class_name]["text"]
    body = text[method["body_start"] : method["body_end"]]
    base_line = line_for_offset(text, method["body_start"])
    calls = []

    for match in re.finditer(r"\bnew\s+([A-Z]\w*)\s*\(", body):
        calls.append(
            {
                "line": base_line + body.count("\n", 0, match.start()),
                "receiver": match.group(1),
                "method": "<init>",
            }
        )

    for match in re.finditer(r"(?<![.\w])([A-Za-z_]\w*)\s*\(", body):
        name = match.group(1)
        if name in LOCAL_CALL_KEYWORDS:
            continue
        prefix = body[: match.start()].rstrip()
        previous = re.search(r"(\w+)\s*$", prefix)
        if previous and previous.group(1) == "new":
            continue
        calls.append(
            {
                "line": base_line + body.count("\n", 0, match.start()),
                "receiver": "this",
                "method": name,
            }
        )

    return calls


def parse_semgrep_calls(results):
    calls = []
    for result in results:
        message = result.get("extra", {}).get("message", "")
        line = result.get("start", {}).get("line")
        if message.startswith("object-call "):
            target = message[len("object-call ") :]
            if "." not in target:
                continue
            receiver, method = target.rsplit(".", 1)
            calls.append({"line": line, "receiver": receiver, "method": method})
    return calls


def resolve_call(call, class_name, types, classes, implementors):
    receiver = call["receiver"]
    method = call["method"]

    if receiver == "this":
        target_type = class_name
    elif receiver in types:
        target_type = types[receiver]
    elif receiver in classes:
        target_type = receiver
    elif method == "<init>":
        target_type = receiver if receiver in classes else None
    else:
        target_type = None

    resolved = []
    if target_type in classes:
        resolved.append(target_type)
        for impl in subtype_closure(target_type, implementors):
            if impl not in resolved:
                resolved.append(impl)

    return {
        "line": call["line"],
        "receiver": receiver,
        "method": method,
        "target_type": target_type,
        "resolved_classes": resolved,
    }


def trace(root_class, root_method, max_depth, classes, methods, implementors, engine, semgrep_timeout):
    queue = deque([(root_class, root_method, 0)])
    seen = set()
    graph = {}

    while queue:
        class_name, method_name, depth = queue.popleft()
        key = (class_name, method_name)
        if key in seen:
            continue
        seen.add(key)

        if class_name not in classes or method_name not in methods.get(class_name, {}):
            graph[key] = {"missing": True, "calls": []}
            continue

        types = infer_types(class_name, method_name, classes, methods)
        semgrep_results = None
        if engine == "semgrep":
            semgrep_results = run_semgrep(class_name, method_name, classes, semgrep_timeout)
        raw_calls = parse_semgrep_calls(semgrep_results) if semgrep_results is not None else fallback_calls(class_name, method_name, classes, methods)
        raw_calls.extend(parser_extra_calls(class_name, method_name, classes, methods))
        calls = []
        raw_seen = set()
        for call in raw_calls:
            dedupe_key = (call["line"], call["receiver"], call["method"])
            if dedupe_key in raw_seen:
                continue
            raw_seen.add(dedupe_key)
            calls.append(resolve_call(call, class_name, types, classes, implementors))

        graph[key] = {"missing": False, "calls": calls}

        if depth < max_depth:
            for call in calls:
                for resolved_class in call["resolved_classes"]:
                    if call["method"] in methods.get(resolved_class, {}):
                        queue.append((resolved_class, call["method"], depth + 1))

    return graph


def print_graph(graph, classes, methods):
    for (class_name, method_name), data in graph.items():
        print("%s.%s()" % (class_name, method_name))
        if data["missing"]:
            print("  method body not found in indexed project sources")
            continue

        calls = sorted(data["calls"], key=lambda call: (call["line"], call["receiver"], call["method"]))
        if not calls:
            print("  (no direct calls found)")
            continue

        for call in calls:
            target = call["target_type"] or "unresolved"
            resolved = ""
            if call["resolved_classes"]:
                resolved = " -> " + ", ".join(
                    "%s.%s()" % (resolved_class, call["method"])
                    for resolved_class in call["resolved_classes"]
                    if call["method"] == "<init>" or call["method"] in methods.get(resolved_class, {})
                )
            print(
                "  line %(line)s: %(receiver)s.%(method)s() [%(target)s]%(resolved)s"
                % {
                    "line": call["line"],
                    "receiver": call["receiver"],
                    "method": call["method"],
                    "target": target,
                    "resolved": resolved,
                }
            )
        print("")


def dot_escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def dot_node_id(class_name, method_name):
    return "%s.%s" % (class_name, method_name)


def print_dot_graph(graph, classes, methods):
    nodes = {}
    edges = set()

    def add_node(node_id, label, style=None):
        attrs = {'label': label}
        if style:
            attrs['style'] = style
        nodes[node_id] = attrs

    def call_node(call):
        target = call["target_type"] or "unresolved"
        node_id = "call:%s:%s:%s" % (target, call["receiver"], call["method"])
        label = "%s.%s()" % (target, call["method"])
        if target == "unresolved":
            label = "%s.%s()" % (call["receiver"], call["method"])
        return node_id, label

    for (class_name, method_name), data in graph.items():
        caller = dot_node_id(class_name, method_name)
        add_node(caller, "%s.%s()" % (class_name, method_name), "dashed" if data["missing"] else None)

        if data["missing"]:
            continue

        for call in data["calls"]:
            added_resolved_edge = False
            for resolved_class in call["resolved_classes"]:
                if call["method"] != "<init>" and call["method"] not in methods.get(resolved_class, {}):
                    continue
                callee = dot_node_id(resolved_class, call["method"])
                add_node(callee, "%s.%s()" % (resolved_class, call["method"]))
                edges.add(
                    (
                        caller,
                        callee,
                        "line %s: %s.%s()" % (call["line"], call["receiver"], call["method"]),
                    )
                )
                added_resolved_edge = True

            if not added_resolved_edge:
                callee, label = call_node(call)
                add_node(callee, label, "dashed")
                edges.add(
                    (
                        caller,
                        callee,
                        "line %s: %s.%s()" % (call["line"], call["receiver"], call["method"]),
                    )
                )

    print("digraph method_calls {")
    print('  graph [rankdir="LR"];')
    print('  node [shape="box"];')

    for node_id, attrs_by_name in sorted(nodes.items()):
        attrs = [
            '%s="%s"' % (name, dot_escape(value))
            for name, value in sorted(attrs_by_name.items())
        ]
        print('  "%s" [%s];' % (dot_escape(node_id), ", ".join(attrs)))

    for caller, callee, label in sorted(edges):
        print(
            '  "%s" -> "%s" [label="%s"];'
            % (dot_escape(caller), dot_escape(callee), dot_escape(label))
        )

    print("}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("class_name", help="Simple or fully-qualified class name, e.g. QuoteDataBean")
    parser.add_argument("method_name", help="Method name, e.g. getSymbol")
    parser.add_argument("--depth", type=int, default=1, help="Recurse into project methods to this depth")
    parser.add_argument(
        "--engine",
        choices=("parser", "semgrep"),
        default="parser",
        help="Use the fast parser matcher or Semgrep for receiver-qualified calls",
    )
    parser.add_argument("--semgrep-timeout", type=int, default=10, help="Seconds to wait for each Semgrep scan")
    parser.add_argument("--dot", action="store_true", help="Output findings as Graphviz DOT")
    args = parser.parse_args()

    classes, methods, implementors = build_index()
    class_name = resolve_class(args.class_name, classes)
    if not class_name:
        raise SystemExit("Class not found in project sources: %s" % args.class_name)
    if args.method_name not in methods.get(class_name, {}):
        raise SystemExit("Method not found in %s: %s" % (class_name, args.method_name))

    graph = trace(
        class_name,
        args.method_name,
        args.depth,
        classes,
        methods,
        implementors,
        args.engine,
        args.semgrep_timeout,
    )
    if args.dot:
        print_dot_graph(graph, classes, methods)
    else:
        print_graph(graph, classes, methods)


if __name__ == "__main__":
    main()
