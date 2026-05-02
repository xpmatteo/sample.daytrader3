#!/usr/bin/env python3
"""List bean-like method calls made by a DayTrader UI entry point.

This is a lightweight static analyzer for the JSP/Facelet style used in this
repository. It is intentionally conservative: it reports calls that are visible
in the page template itself, not every method transitively invoked by services.
"""

import argparse
import os
import re
import sys
from collections import defaultdict


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEBAPP_ROOT = os.path.join(REPO_ROOT, "daytrader3-ee6-web", "src", "main", "webapp")
JAVA_ROOTS = [
    os.path.join(REPO_ROOT, "daytrader3-ee6-web", "src", "main", "java"),
    os.path.join(REPO_ROOT, "daytrader3-ee6-ejb", "src", "main", "java"),
    os.path.join(REPO_ROOT, "daytrader3-ee6-rest", "src", "main", "java"),
]


METHOD_RE = re.compile(
    r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?"
    r"([\w.$<>?,\s\[\]]+?)\s+(\w+)\s*\("
)
CLASS_RE = re.compile(r"\b(?:class|interface)\s+(\w+)\b")
PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
MANAGED_BEAN_RE = re.compile(r"@ManagedBean(?:\s*\(\s*(?:name\s*=\s*)?\"([^\"]+)\"\s*\))?")


def decap(name):
    return name[:1].lower() + name[1:] if name else name


def normalize_type(type_name):
    type_name = re.sub(r"<.*>", "", type_name)
    type_name = type_name.replace("[]", "")
    return type_name.strip().split(".")[-1]


def property_getter(prop):
    return "get" + prop[:1].upper() + prop[1:]


def line_for_offset(text, offset):
    return text.count("\n", 0, offset) + 1


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def resolve_entrypoint(arg):
    cleaned = arg.lstrip("/")
    candidates = []

    if cleaned.endswith(".jsf"):
        cleaned = cleaned[:-4] + ".xhtml"

    if os.path.isabs(cleaned):
        candidates.append(cleaned)
    else:
        candidates.append(os.path.join(WEBAPP_ROOT, cleaned))
        candidates.append(os.path.join(WEBAPP_ROOT, os.path.basename(cleaned)))

    for root, _, files in os.walk(WEBAPP_ROOT):
        for filename in files:
            if filename == os.path.basename(cleaned):
                candidates.append(os.path.join(root, filename))

    for candidate in candidates:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    raise SystemExit("Entry point not found under webapp: %s" % arg)


def build_java_index():
    classes = {}
    methods = defaultdict(dict)
    managed_beans = {}

    for root in JAVA_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                path = os.path.join(dirpath, filename)
                text = read_text(path)
                package_match = PACKAGE_RE.search(text)
                class_match = CLASS_RE.search(text)
                if not class_match:
                    continue

                package = package_match.group(1) if package_match else ""
                simple_name = class_match.group(1)
                fqn = package + "." + simple_name if package else simple_name
                classes[simple_name] = {"fqn": fqn, "path": path}

                managed_match = MANAGED_BEAN_RE.search(text)
                if managed_match:
                    managed_name = managed_match.group(1) or decap(simple_name)
                    managed_beans[managed_name] = simple_name

                for method_match in METHOD_RE.finditer(text):
                    return_type = normalize_type(method_match.group(1))
                    method_name = method_match.group(2)
                    methods[simple_name][method_name] = return_type

    return classes, methods, managed_beans


def imports_for_page(text):
    imports = {}
    wildcard_packages = []

    for directive in re.findall(r"<%@\s*page\b[^%]*%>", text, flags=re.DOTALL):
        for attr in re.findall(r'import\s*=\s*"([^"]+)"', directive):
            for item in attr.split(","):
                item = item.strip()
                if not item:
                    continue
                if item.endswith(".*"):
                    wildcard_packages.append(item[:-2])
                else:
                    imports[item.split(".")[-1]] = item

    return imports, wildcard_packages


def infer_variables(text):
    variables = {}

    for match in re.finditer(r"<jsp:useBean\b([^>]*)>", text):
        attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', match.group(1)))
        bean_id = attrs.get("id")
        bean_type = attrs.get("type") or attrs.get("class")
        if bean_id and bean_type:
            variables[bean_id] = normalize_type(bean_type)

    declaration_patterns = [
        r"\b([A-Z]\w+(?:<[^;=]+>)?)\s+(\w+)\s*=",
        r"\b([A-Z]\w+)\s+(\w+)\s*;",
        r"\b(\w+)\s*=\s*\(([A-Z]\w+)\)\s*request\.getAttribute",
        r"\b([A-Z]\w+)\s+(\w+)\s*=\s*\([^)]+\)\s*\w+\.next\s*\(",
    ]

    for pattern in declaration_patterns:
        for match in re.finditer(pattern, text):
            if pattern.startswith(r"\b(\w+)"):
                var_name = match.group(1)
                type_name = match.group(2)
            else:
                type_name = match.group(1)
                var_name = match.group(2)
            type_name = normalize_type(type_name)
            if type_name not in {
                "String",
                "int",
                "double",
                "boolean",
                "Integer",
                "Collection",
                "Iterator",
                "Enumeration",
                "BigDecimal",
            }:
                variables[var_name] = type_name

    return variables


def is_bean_like(type_name):
    return (
        type_name.endswith("Bean")
        or type_name.endswith("DataBean")
        or type_name in {"TradeConfig", "QuoteBean", "AccountBean"}
    )


def find_scriptlet_calls(text, variables, classes):
    calls = []
    identifiers = set(variables) | set(classes)
    if not identifiers:
        return calls

    call_re = re.compile(r"\b(" + "|".join(re.escape(i) for i in sorted(identifiers, key=len, reverse=True)) + r")\.(\w+)\s*\(")
    for match in call_re.finditer(text):
        target = match.group(1)
        method = match.group(2)
        if target in variables:
            type_name = variables[target]
            if is_bean_like(type_name):
                calls.append((line_for_offset(text, match.start()), type_name, method, target))
        elif target in classes and is_bean_like(target):
            calls.append((line_for_offset(text, match.start()), target, method, target))

    return calls


def find_el_calls(text, managed_beans, methods):
    calls = []

    for match in re.finditer(r"[#$]\{([^}]+)\}", text):
        expr = match.group(1).strip()
        path = re.split(r"\s|\(|\[", expr, maxsplit=1)[0]
        parts = [part for part in path.split(".") if part]
        if not parts or parts[0] not in managed_beans:
            continue

        current_type = managed_beans[parts[0]]
        target_name = parts[0]
        for part in parts[1:]:
            if part.endswith("()"):
                method_name = part[:-2]
            else:
                method_name = property_getter(part)

            calls.append((line_for_offset(text, match.start()), current_type, method_name, target_name))
            current_type = methods.get(current_type, {}).get(method_name, current_type)
            target_name = part

    return calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrypoint", help="JSP/XHTML/JSF entry point, e.g. displayQuote.jsp")
    args = parser.parse_args()

    entrypoint = resolve_entrypoint(args.entrypoint)
    text = read_text(entrypoint)
    rel = os.path.relpath(entrypoint, WEBAPP_ROOT)

    classes, methods, managed_beans = build_java_index()
    imports, _ = imports_for_page(text)
    variables = infer_variables(text)

    known_classes = set(classes) | set(imports)
    calls = find_scriptlet_calls(text, variables, known_classes)
    calls.extend(find_el_calls(text, managed_beans, methods))

    unique = sorted(set(calls), key=lambda item: (item[0], item[1], item[2], item[3]))

    print("Entry point: /%s" % rel)
    bean_variables = {name: type_name for name, type_name in variables.items() if is_bean_like(type_name)}
    if bean_variables:
        print("\nInferred page beans/variables:")
        for name in sorted(bean_variables):
            print("  %s: %s" % (name, bean_variables[name]))

    print("\nBean method calls:")
    if not unique:
        print("  (none found)")
        return

    by_type = defaultdict(list)
    for line, type_name, method, target in unique:
        by_type[type_name].append((method, target, line))

    for type_name in sorted(by_type):
        print("  %s" % type_name)
        for method, target, line in sorted(by_type[type_name], key=lambda item: (item[0], item[2], item[1])):
            print("    - %s() via %s at line %d" % (method, target, line))


if __name__ == "__main__":
    main()
