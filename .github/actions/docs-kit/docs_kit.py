#!/usr/bin/env python3
"""WanAware documentation kit: scaffold and check the standard documentation set.

The standard is the one Asset Pipeline (wanaware/asset-pipeline) uses: its documents,
templates and rules (docs/templates/service/, docs/10-documentation-standards.md), and this
script generalizes its checker (scripts/check-docs.py) for any repository.

Every repository documents itself with the same files: docs/README.md (overview and
index), docs/01-architecture.md to docs/08-development.md, docs/09-glossary.md and
docs/10-documentation-standards.md. In a monorepo, every service under the components
directory (services/ by default) also gets the per-service set in
services/<service>/docs/. docs/10-documentation-standards.md explains the rules.

Run from anywhere inside the repository:

    python3 docs/templates/docs_kit.py check                       # structure, links, diagrams
    python3 docs/templates/docs_kit.py check --allow-placeholders  # tolerate unfilled skeletons
    python3 docs/templates/docs_kit.py scaffold                    # add missing documents
    python3 docs/templates/docs_kit.py list --mermaid              # documents with diagrams

Each repository keeps a copy of this script in docs/templates/, next to the templates
it checks against; docs/templates/docs-kit.json holds the repository's settings. The
source is wanaware/.github (.github/actions/docs-kit), and the Documentation workflow
keeps the copy current. Exit code 0 when everything passes.

Standard library only; Python 3.9 or later.
"""
import argparse
import bisect
import datetime
import json
import os
import posixpath
import re
import subprocess
import sys
from urllib.parse import unquote

SCHEMA = 1
KIT_HOME = "https://github.com/wanaware/.github/tree/prod/.github/actions/docs-kit"
KIT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = "docs/templates"
CONFIG_FILE = "docs-kit.json"
SCRIPT_FILE = "docs_kit.py"
TEMPLATE_SETS = ("component", "platform", "shared")
LAYOUTS = ("single", "monorepo")
DEFAULTS = {
    "schema": SCHEMA,
    "name": "",
    "repository": "",
    "layout": "",
    "components_dir": "services",
    "exclude": [],
    "branch": "dev",
}

STANDARD_RE = re.compile(r"^(README|\d\d-[a-z0-9-]+)\.md$")
FENCE_RE = re.compile(r"^( *)(`{3,}|~{3,})(.*)$")
LIST_ITEM_RE = re.compile(r"^( *)([-+*]|\d{1,9}[.)])( +|$)")
# [text](destination "title"): the destination is <anything> or text with balanced parentheses.
LINK_RE = re.compile(
    r'!?\[(?:[^\[\]]|\[[^\]]*\])*\]'
    r'\(\s*(?:<([^<>\n]*)>|((?:[^()\s]|\([^()\s]*\))+))'
    r'(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^()]*\)))?\s*\)')
# [label]: destination "title" (a reference definition; [^label] is a footnote, not a link).
REF_DEF_RE = re.compile(
    r'^ {0,3}\[(?!\^)[^\]]+\]:\s*(?:<([^<>\n]*)>|(\S+))'
    r'(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^()]*\)))?\s*$')
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")  # underline of a Setext heading
REF_USE_RE = re.compile(r"\[([^\[\]]+)\]\[([^\[\]]*)\]|\[([^\[\]]+)\](?![\[(:])")  # [t][l], [l][], [l]
FOOTNOTE_DEF_RE = re.compile(r"^ {0,3}\[\^[^\]]+\]:")  # a footnote definition, any text after it
HTML_ANCHOR_RE = re.compile(r'<a\s+(?:name|id)="([^"]+)"', re.I)
QUOTE_RE = re.compile(r"^ {0,3}> ?")  # one level of block quote marker
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")  # a span closes on the same run length
FRONT_RE = re.compile(r"^<!--\s*docs-kit:(.*?)-->\s*$")
ATTR_RE = re.compile(r'([a-z][a-z-]*)(?:="([^"]*)")?')
TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
COND_RE = re.compile(r"^\s*\{\{([#/])(single|monorepo)\}\}\s*$")
INLINE_COND_RE = re.compile(r"\{\{#(single|monorepo)\}\}(.*?)\{\{/\1\}\}")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
ANGLE_RE = re.compile(r"<[^<>]+>")  # may wrap onto following lines; see placeholder_tokens
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATE_TOKEN = "YYYY-MM-DD"
SHA_TOKEN = "<short-sha>"
GUIDE_MARK = "TEMPLATE:"
HTML_TAGS = {
    "a", "abbr", "b", "br", "code", "details", "div", "em", "hr", "i", "img", "kbd", "li",
    "ol", "p", "picture", "pre", "source", "span", "strong", "sub", "summary", "sup",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
MERMAID_TYPES = ("flowchart", "sequenceDiagram", "classDiagram", "erDiagram", "stateDiagram-v2")
MERMAID_FORBIDDEN = re.compile(r"^\s*(click|style|linkStyle)\b")
MERMAID_COLOUR = re.compile(r"(?<![\w-])(fill|color|stroke|background(?:-color)?)\s*:")


class KitError(Exception):
    """A problem with the kit's own configuration or templates (not with a document)."""


# --------------------------------------------------------------------------- Markdown


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def scan(lines):
    """Yield (lineno, line, info, delimiter) for every line.

    info is None outside fenced code blocks. Inside one, including its opening and
    closing fence lines, it is the opening fence's info string ("" when there is
    none), and delimiter says whether the line is one of the fence lines.

    Follows CommonMark closely enough for these checks:
    - A fence opens on a run of three or more backticks or tildes indented at
      most three spaces beyond the content of the enclosing list item, or
      beyond the margin outside lists. A deeper run is indented code, not a
      fence. A backtick run followed by text containing a backtick is inline
      code.
    - A fence closes only on a line of the same character, at least as long,
      indented at most three spaces beyond the opening fence's container, with
      nothing after it. A four-backtick example may therefore contain
      triple-backtick fences.
    - An HTML comment that starts a line (up to three spaces in) runs to the line
      containing "-->", and nothing inside it is a fence, as GitHub hides it all.
    """
    fence = None  # (character, length, container offset, info) of the open fence
    containers = []  # content offsets of the enclosing list items
    html_comment = False  # inside an HTML comment that started a line (GitHub hides it, fences too)
    for i, line in enumerate(lines, 1):
        text = line.expandtabs(4)
        if fence is None:
            if html_comment:
                html_comment = "-->" not in text
                yield i, line, None, False
                continue
            opener = re.match(r" {0,3}<!--", text)
            if opener and "-->" not in text[opener.end():]:
                html_comment = True
                yield i, line, None, False
                continue
        indent = len(text) - len(text.lstrip(" "))
        m = FENCE_RE.match(text)
        if fence is not None:
            char, length, base, info = fence
            closing = (m and m.group(2)[0] == char and len(m.group(2)) >= length
                       and not m.group(3).strip() and indent <= base + 3)
            if closing:
                fence = None
            yield i, line, info, bool(closing)
            continue
        if text.strip():
            while containers and indent < containers[-1]:
                containers.pop()
            # A line can open several items at once ("- - item", "1. - item"),
            # so read every list marker before the content.
            pos = 0
            item = LIST_ITEM_RE.match(text)
            while item:
                gap = len(item.group(3))
                pos += len(item.group(1)) + len(item.group(2)) + (gap if 1 <= gap <= 4 else 1)
                containers.append(pos)
                item = LIST_ITEM_RE.match(text[pos:]) if 1 <= gap <= 4 else None
        base = containers[-1] if containers else 0
        if m and indent <= base + 3 and not (m.group(2)[0] == "`" and "`" in m.group(3)):
            fence = (m.group(2)[0], len(m.group(2)), base, m.group(3).strip())
            yield i, line, fence[3], True
            continue
        yield i, line, None, False


def outside_fences(lines):
    """Yield (lineno, line) for lines that are not inside fenced code blocks."""
    for i, line, info, _ in scan(lines):
        if info is None:
            yield i, line


def visible_lines(lines, keep_code=False, dequote=False):
    """[(lineno, text)] for every line, with HTML comments removed and text None inside
    fenced code. Inline code is kept (keep_code) or removed. With dequote, the content of a
    block quote is read as Markdown in its own right (its "> " markers removed), so a code
    fence inside a quote is code too.

    Reads each line left to right, so a comment marker inside a code span (Write `<!--` to
    start a comment) is example text, not the start of a comment."""
    result, quote = [], []

    def flush_quote():
        if quote:
            inner = visible_lines([t for _, t in quote], keep_code, dequote)
            result.extend((quote[n - 1][0], text) for n, text in inner)
            quote.clear()

    in_comment = False
    for i, line, info, _ in scan(lines):
        if dequote and info is None and not in_comment and QUOTE_RE.match(line):
            quote.append((i, QUOTE_RE.sub("", line, count=1)))
            continue
        flush_quote()
        if info is not None:
            result.append((i, None))
            continue
        out, rest = "", line
        block_start = re.match(r" {0,3}<!--", line) is not None
        while rest:
            if in_comment:
                end = rest.find("-->")
                if end < 0:
                    rest = ""
                else:
                    rest, in_comment = rest[end + 3:], False
                continue
            start = rest.find("<!--")
            code = INLINE_CODE_RE.search(rest)
            if code and (start < 0 or code.start() < start):
                out = out + rest[:code.end() if keep_code else code.start()]
                rest = rest[code.end():]
            elif start < 0:
                out, rest = out + rest, ""
            elif (block_start and not out) or comment_closes(lines, i, rest[start + 4:]):
                out, rest, in_comment = out + rest[:start], rest[start + 4:], True
            else:  # a stray "<!--" inside a paragraph is text, as on GitHub
                out, rest = out + rest[:start + 4], rest[start + 4:]
        result.append((i, out))
    flush_quote()
    return result


def comment_closes(lines, lineno, rest):
    """Whether an inline comment opened on line lineno closes before its paragraph ends."""
    if "-->" in rest:
        return True
    for line in lines[lineno:]:
        if not line.strip():
            return False
        if "-->" in line:
            return True
    return False


def prose(lines):
    """Yield (lineno, text) outside code (block quotes included) and HTML comments."""
    for i, text in visible_lines(lines, dequote=True):
        if text is not None:
            yield i, text


def mermaid_blocks(lines):
    """Return [(first_lineno, [(lineno, line), ...])] for every visible ```mermaid block
    (scan() does not see fences inside HTML comments, which GitHub hides)."""
    blocks, current = [], None
    for i, line, info, delimiter in scan(lines):
        is_mermaid = info is not None and info.split()[:1] == ["mermaid"]
        if delimiter and is_mermaid and current is None:
            current = (i, [])
        elif delimiter and current is not None:
            blocks.append(current)
            current = None
        elif current is not None:
            current[1].append((i, line))
    if current is not None:
        blocks.append(current)
    return blocks


def heading_list(lines, nested=False):
    """[(lineno, level, text)] for the headings GitHub renders, in order: ATX (# Title) and
    Setext (a paragraph underlined with === or ---), outside code and HTML comments.

    By default only headings that start a line count, as the document's own sections. With
    nested, ATX headings indented up to three spaces and headings inside block quotes count
    too, since GitHub gives them anchors as well. A block quote's content is Markdown in its
    own right, so it is read the same way (code fences inside it included)."""
    out, para, quote = [], [], []

    def flush_quote():
        if quote:
            inner = heading_list([t for _, t in quote], nested=True)
            out.extend((quote[n - 1][0], level, title) for n, level, title in inner)
            quote.clear()

    for i, text in visible_lines(lines, keep_code=True):
        if nested and text is not None and re.match(r" {0,3}>", text):
            quote.append((i, re.sub(r"^ {0,3}> ?", "", text)))
            para = []
            continue
        flush_quote()
        if text is None or not text.strip():
            para = []
            continue
        m = HEADING_RE.match(re.sub(r"^ {0,3}", "", text) if nested else text)
        if m:
            out.append((i, len(m.group(1)), m.group(2)))
            para = []
        elif SETEXT_RE.match(text) and para:
            out.append((para[0][0], 1 if text.strip()[0] == "=" else 2, " ".join(t for _, t in para)))
            para = []
        elif LIST_ITEM_RE.match(text) or text.lstrip().startswith(">") or \
                (not para and (REF_DEF_RE.match(text) or FOOTNOTE_DEF_RE.match(text))):
            para = []  # not paragraph text, so an underline after it is a rule, not a heading
        else:
            para.append((i, text.strip()))
    flush_quote()
    return out


def headings(lines, level):
    return [text for _, lvl, text in heading_list(lines) if lvl == level]


def first_heading(lines):
    for i, line in outside_fences(lines):
        if line.startswith("# "):
            return i, line.strip()
    return None, ""


def first_content_lines(lines, n):
    """First n (lineno, text) non-empty lines after the H1, skipping HTML comments."""
    out, seen_h1, in_comment = [], False, False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not seen_h1:
            seen_h1 = s.startswith("# ")
            continue
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        if s:
            out.append((i, s))
            if len(out) == n:
                break
    return out


def github_slug(text):
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


_anchor_cache = {}


def anchors_for(path):
    if path not in _anchor_cache:
        slugs, counts = set(), {}
        lines = read_lines(path)
        for _, text in prose(lines):
            slugs.update(HTML_ANCHOR_RE.findall(text))
        for _, _, text in heading_list(lines, nested=True):
            # Number repeats as GitHub does: Foo, Foo, Foo 1 -> foo, foo-1, foo-1-1.
            base = slug = github_slug(text)
            while slug in counts:
                counts[base] += 1
                slug = f"{base}-{counts[base]}"
            counts[slug] = 0
            slugs.add(slug)
        _anchor_cache[path] = {s.lower() for s in slugs}
    return _anchor_cache[path]


def label_key(label):
    return " ".join(label.split()).lower()


def used_labels(texts):
    """Reference labels used by [text][label], [label][] or [label] links, including labels
    that wrap onto the next line of their paragraph."""
    joined = "\n".join("" if REF_DEF_RE.match(t) else t for t in texts)
    used = set()
    for m in REF_USE_RE.finditer(joined):
        if re.search(r"\n[ \t]*\n", m.group(0)):
            continue  # brackets in different paragraphs
        label = (m.group(2) or m.group(1)) if m.group(1) is not None else m.group(3)
        used.add(label_key(label))
    return used


def relative_links(lines, unused_definitions=True):
    """Yield (lineno, target) for every relative link, image and reference definition outside code
    and HTML comments (readers cannot see or follow a link in a comment). Without
    unused_definitions, definitions that no link uses (and so render nothing) are left out."""
    entries = list(prose(lines))
    used = None if unused_definitions else used_labels(text for _, text in entries)
    found = []  # (lineno, order, target)
    # Inline links and images may wrap onto the next lines of their paragraph.
    starts, offset = [], 0
    for _, text in entries:
        starts.append(offset)
        offset += len(text) + 1
    joined = "\n".join(text for _, text in entries)
    for m in LINK_RE.finditer(joined):
        if re.search(r"\n[ \t]*\n", m.group(0)):
            continue  # a "[" and a "](" in different paragraphs
        lineno = entries[bisect.bisect_right(starts, m.start()) - 1][0]
        found.append((lineno, m.start(), m.group(1) if m.group(1) is not None else m.group(2)))
    for lineno, text in entries:
        ref = REF_DEF_RE.match(text)
        if ref and (used is None or label_key(re.match(r" {0,3}\[([^\]]+)\]", text).group(1)) in used):
            found.append((lineno, offset, ref.group(1) if ref.group(1) is not None else ref.group(2)))
    for lineno, _, target in sorted(found):
        if target and not target.startswith("//") and not re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            yield lineno, target


def resolve(root, base, path):
    """The file a link path points at: relative to the document, or to the repository root
    when it starts with / (as GitHub resolves it)."""
    if path.startswith("/"):
        return os.path.normpath(os.path.join(root, path.lstrip("/")))
    return os.path.normpath(os.path.join(base, path))


def split_target(target):
    """Return the decoded (path, fragment) of a link destination, without its query string."""
    path, _, fragment = target.partition("#")
    return unquote(path.partition("?")[0]), unquote(fragment)


def is_placeholder(token):
    inner = token[1:-1].strip()
    if not inner or inner[0] in "/!" or re.match(r"^[a-z][a-z0-9+.-]*:", inner, re.I):
        return False
    if re.search(r"\n[ \t]*\n", inner):  # a "<" and a ">" in different paragraphs
        return False
    tag = re.match(r"[A-Za-z][A-Za-z0-9-]*", inner)
    if not tag or tag.group(0).lower() not in HTML_TAGS:
        return True
    rest = inner[len(tag.group(0)):].strip()
    return not (rest in ("", "/") or "=" in rest)  # <br>, <br/>, <a name="x"> are HTML


# --------------------------------------------------------------------------- Templates


class Template:
    """A template file. Its first line may be a front-matter comment:

        <!-- docs-kit: nav="Data model" managed free-headings -->

    nav is the label in the navigation bar; managed documents are generated by the
    kit and regenerated on refresh; free-headings documents have no fixed H2 list.
    """

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        first, _, rest = text.partition("\n")
        m = FRONT_RE.match(first)
        attrs = dict(ATTR_RE.findall(m.group(1))) if m else {}
        self.body = rest.lstrip("\n") if m else text
        self.nav = attrs.get("nav") or self.name
        self.managed = "managed" in attrs
        self.free_headings = "free-headings" in attrs


def order(names):
    return sorted(names, key=lambda n: (n != "README.md", n))


def load_templates(directory):
    if not os.path.isdir(directory):
        raise KitError(f"template directory {directory} not found")
    names = order(f for f in os.listdir(directory) if STANDARD_RE.match(f))
    return [Template(os.path.join(directory, n)) for n in names]


class DocSet:
    """One documentation set: the repository-level docs/ or one service's docs/."""

    def __init__(self, kind, name, base, templates):
        self.kind = kind  # "root" or "component"
        self.name = name
        self.base = base  # path from the repository root; "." for the root set
        self.docs_dir = "docs" if base == "." else posixpath.join(base, "docs")
        self.templates = sorted(templates, key=lambda t: (t.name != "README.md", t.name))


def components(root, cfg):
    directory = os.path.join(root, cfg["components_dir"])
    if not os.path.isdir(directory):
        return []
    return sorted(
        d for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d)) and not d.startswith(".")
        and d not in cfg["exclude"]
    )


def doc_sets(root, cfg, template_dir):
    comp = load_templates(os.path.join(template_dir, "component"))
    shared = load_templates(os.path.join(template_dir, "shared"))
    if cfg["layout"] == "single":
        return [DocSet("root", cfg["name"], ".", comp + shared)]
    platform = load_templates(os.path.join(template_dir, "platform"))
    sets = [DocSet("root", cfg["name"], ".", platform + shared)]
    for c in components(root, cfg):
        sets.append(DocSet("component", c, posixpath.join(cfg["components_dir"], c), comp))
    return sets


def nav_bar(ds, page, docs_root):
    parts = [f"**{t.nav}**" if t.name == page else f"[{t.nav}]({t.name})" for t in ds.templates]
    if ds.kind == "component":
        parts.append(f"[Platform docs]({docs_root}/README.md)")
    return " · ".join(parts)


def meta_line(cfg, ds):
    verified = f"**Last verified against source:** {DATE_TOKEN} (`{cfg['branch']}` @ `{SHA_TOKEN}`)"
    if ds.kind == "component":
        return f"> **Service:** `{ds.base}` · {verified}"
    if cfg["layout"] == "monorepo":
        return f"> **Scope:** all services in this monorepo · {verified}"
    return f"> **Repository:** `{cfg['repository']}` · {verified}"


def service_table(comps, root_rel):
    if not comps:
        return "_No services yet: each directory under the components directory becomes one._"
    rows = ["| Service | Role | Documentation |", "|---|---|---|"]
    for c in comps:
        rows.append(f"| [`{c.name}`]({root_rel}/{c.base}) | <role> | [docs]({root_rel}/{c.docs_dir}/README.md) |")
    return "\n".join(rows)


def service_matrix(comps, root_rel):
    if not comps:
        return "_No services yet._"
    tmpl = comps[0].templates
    rows = ["| Service | " + " | ".join(t.nav for t in tmpl) + " |",
            "|---|" + "---|" * len(tmpl)]
    for c in comps:
        cells = []
        for t in tmpl:
            label = "README" if t.name == "README.md" else t.name[:2]
            cells.append(f"[{label}]({root_rel}/{c.docs_dir}/{t.name})")
        rows.append(f"| {c.name} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def context(cfg, ds, sets, page):
    root_rel = posixpath.relpath(".", ds.docs_dir)
    docs_root = posixpath.relpath("docs", ds.docs_dir)
    comps = [s for s in sets if s.kind == "component"]
    repo_dir = cfg["repository"].split("/")[-1] or ds.name
    return {
        "NAME": ds.name,
        "NAV": nav_bar(ds, page, docs_root),
        "META": meta_line(cfg, ds),
        "REPO": cfg["repository"],
        "BRANCH": cfg["branch"],
        "ROOT": root_rel,
        "DOCS_ROOT": docs_root,
        "DOCS_PATH": ds.docs_dir,
        "SET_DIR": ds.base if ds.base != "." else repo_dir,
        "REPO_DIR": repo_dir,
        "COMPONENTS_DIR": cfg["components_dir"],
        "SERVICE_TABLE": service_table(comps, root_rel),
        "SERVICE_MATRIX": service_matrix(comps, root_rel),
        "KIT_HOME": KIT_HOME,
    }


def render(tmpl, ctx, layout):
    """Render a template: keep only this layout's {{#single}}/{{#monorepo}} blocks (whole
    lines, or inline within one line), then substitute {{TOKENS}}."""
    out, stack = [], []
    for n, line in enumerate(tmpl.body.split("\n"), 1):
        m = COND_RE.match(line)
        if m:
            if m.group(1) == "#":
                stack.append((m.group(2), m.group(2) == layout))
            elif not stack or stack[-1][0] != m.group(2):
                raise KitError(f"{tmpl.path}: line {n}: unmatched {line.strip()}")
            else:
                stack.pop()
            continue
        if all(keep for _, keep in stack):
            out.append(INLINE_COND_RE.sub(lambda c: c.group(2) if c.group(1) == layout else "", line))
    if stack:
        raise KitError(f"{tmpl.path}: unclosed {{{{#{stack[-1][0]}}}}} block")
    text = "\n".join(out)
    if ctx["DOCS_ROOT"] == ".":
        text = text.replace("{{DOCS_ROOT}}/", "")

    def substitute(m):
        if m.group(1) not in ctx:
            raise KitError(f"{tmpl.path}: unknown token {m.group(0)}")
        return ctx[m.group(1)]

    return TOKEN_RE.sub(substitute, text).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- Configuration


def find_root(arg):
    if arg:
        return os.path.abspath(arg)
    if KIT_DIR.replace(os.sep, "/").endswith("/" + VENDOR_DIR):
        return os.path.dirname(os.path.dirname(KIT_DIR))
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def load_config(root):
    path = os.path.join(root, VENDOR_DIR, CONFIG_FILE)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("schema", 0) > SCHEMA:
        raise KitError(f"{VENDOR_DIR}/{CONFIG_FILE} needs a newer docs kit (schema {data['schema']}); "
                       "refresh docs/templates/ with the Documentation workflow")
    cfg = dict(DEFAULTS)
    cfg.update(data)
    cfg["schema"] = SCHEMA
    if cfg["layout"] not in LAYOUTS:
        raise KitError(f"{VENDOR_DIR}/{CONFIG_FILE}: layout must be one of {', '.join(LAYOUTS)}")
    return cfg


def detect_repository(root):
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    try:
        url = subprocess.run(["git", "-C", root, "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, check=True).stdout.strip()
        parts = [p for p in re.split(r"[/:]", re.sub(r"\.git$", "", url)) if p]
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
    except (OSError, subprocess.CalledProcessError):
        pass
    return os.path.basename(os.path.abspath(root))


def detect_layout(root, cfg):
    return "monorepo" if len(components(root, cfg)) >= 2 else "single"


def kit_files(layout, kit_dir=KIT_DIR):
    files = [SCRIPT_FILE]
    for s in TEMPLATE_SETS:
        if s == "platform" and layout != "monorepo":
            continue
        directory = os.path.join(kit_dir, s)
        if not os.path.isdir(directory):
            raise KitError(f"the kit at {kit_dir} has no {s}/ templates; "
                           "run the scaffold from wanaware/.github (the Documentation workflow)")
        files += [f"{s}/{f}" for f in order(f for f in os.listdir(directory) if STANDARD_RE.match(f))]
    return files


# --------------------------------------------------------------------------- Reporting


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, path, line, msg):
        self.items.append((level, code, path, line, msg))

    def error(self, code, path, line, msg):
        self.add("error", code, path, line, msg)

    def warning(self, code, path, line, msg):
        self.add("warning", code, path, line, msg)

    def notice(self, code, path, line, msg):
        self.add("notice", code, path, line, msg)

    def count(self, level):
        return sum(1 for item in self.items if item[0] == level)

    def emit(self, annotate):
        for level, code, path, line, msg in self.items:
            if annotate:
                props = f"file={path}" + (f",line={line}" if line else "") + f",title=docs {code}"
                text = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::{level} {props}::{text}")
            else:
                loc = f"{path}:{line}" if line else path
                print(f"{level.upper():7} {code:11} {loc}: {msg}")

    def summary_markdown(self, headline):
        out = ["### Documentation check", "", headline, ""]
        shown = [i for i in self.items if i[0] != "notice"][:50]
        if shown:
            out += ["| Level | Check | Location | Problem |", "|---|---|---|---|"]
            for level, code, path, line, msg in shown:
                loc = f"{path}:{line}" if line else path
                out.append(f"| {level} | {code} | `{loc}` | {msg.replace('|', '&#124;')} |")
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- Checks


def meta_problem(want, got):
    """Compare a metadata line with the template's. Returns (kind, message) or None.

    Everything up to the date must match; the date must be real; text after it is free
    (but must not still hold the commit placeholder)."""
    if DATE_TOKEN not in want:
        return None if got == want else ("META", "metadata line differs from the template")
    prefix = want.split(DATE_TOKEN)[0]
    if not got.startswith(prefix):
        return ("META", "metadata line missing or malformed; expected it to start with: " + prefix.strip())
    rest = got[len(prefix):]
    if rest.startswith(DATE_TOKEN) or SHA_TOKEN in rest:
        return ("PLACEHOLDER", "metadata line still has the date or commit placeholder; "
                               "fill in when and against which commit the page was verified")
    try:
        if not DATE_RE.match(rest):
            raise ValueError
        datetime.date.fromisoformat(rest[:10])
    except ValueError:
        return ("META", "metadata line needs a real YYYY-MM-DD date after 'Last verified against source:'")
    return None


def placeholder_findings(want_text, lines):
    """(lineno, message) for template text left in a document."""
    found = []
    text = "\n".join(lines)
    for i, line in outside_fences(lines):
        if GUIDE_MARK in line:
            found.append((i, "template guidance comment (TEMPLATE:) left in"))
    for comment in COMMENT_RE.findall(want_text):
        if GUIDE_MARK in comment:
            continue
        at = text.find(comment)
        if at >= 0:
            found.append((text.count("\n", 0, at) + 1, "template guidance comment left in: "
                          + " ".join(comment[4:-3].split())[:60] + "…"))
    wanted = {token for _, token in placeholder_tokens(want_text.split("\n"))}
    for i, token in placeholder_tokens(lines):
        if token in wanted:
            found.append((i, f"placeholder {token} not filled in"))
    # Code blocks hold examples, so only the placeholders the template itself puts in one count.
    wanted = {token for _, token in code_placeholder_tokens(want_text.split("\n"))}
    for i, token in code_placeholder_tokens(lines):
        if token in wanted:
            found.append((i, f"placeholder {token} not filled in (in a code block)"))
    return sorted(set(found))


def code_placeholder_tokens(lines):
    """Yield (lineno, token) for every <placeholder> inside fenced code blocks."""
    for i, line, info, delimiter in scan(lines):
        if info is not None and not delimiter:
            for token in re.findall(r"<[^<>\n]+>", line):
                if is_placeholder(token):
                    yield i, token


def placeholder_tokens(lines):
    """Yield (lineno, token) for every <placeholder> in prose (outside code and comments).

    A placeholder may wrap onto following lines of its paragraph; the token is returned
    with its whitespace collapsed, so it matches however the lines are wrapped."""
    numbered = list(prose(lines))
    starts, offset = [], 0
    for _, text in numbered:
        starts.append(offset)
        offset += len(text) + 1
    joined = "\n".join(text for _, text in numbered)
    for m in ANGLE_RE.finditer(joined):
        if is_placeholder(m.group(0)):
            lineno = numbered[bisect.bisect_right(starts, m.start()) - 1][0]
            yield lineno, " ".join(m.group(0).split())


def lint_mermaid(lines):
    """(lineno, message) for diagrams that break the diagram conventions."""
    found = []
    for start, body in mermaid_blocks(lines):
        meaningful = [(i, l.strip()) for i, l in body if l.strip() and not l.strip().startswith("%%")]
        for i, l in body:
            if "%%{" in l:
                found.append((i, "no %%{init}%% directives or themes in diagrams"))
            if MERMAID_FORBIDDEN.match(l):
                found.append((i, f"no '{l.split()[0]}' statements in diagrams (no click handlers or colours)"))
            if l.strip().startswith("classDef") and MERMAID_COLOUR.search(l):
                found.append((i, "classDef must not set colours (fill, color, stroke); "
                                 "use stroke-width or stroke-dasharray"))
        if not meaningful:
            found.append((start, "empty Mermaid diagram"))
            continue
        kind = meaningful[0][1].split()[0]
        if kind not in MERMAID_TYPES:
            found.append((meaningful[0][0], f"diagram type '{kind}' is not allowed; use one of "
                          + ", ".join(MERMAID_TYPES)))
        elif kind == "sequenceDiagram" and (len(meaningful) < 2 or meaningful[1][1] != "autonumber"):
            found.append((meaningful[0][0], "sequenceDiagram must start with autonumber"))
    return found


def check_document(root, cfg, sets, ds, tmpl, report, lenient):
    rel = posixpath.join(ds.docs_dir, tmpl.name)
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        report.error("MISSING", rel, None, "standard document is missing; run docs_kit.py scaffold to add it")
        return None
    want_text = render(tmpl, context(cfg, ds, sets, tmpl.name), cfg["layout"])
    want, lines = want_text.split("\n"), read_lines(path)
    if tmpl.managed:
        if "\n".join(lines).rstrip("\n") + "\n" != want_text:
            report.warning("STALE", rel, None, "generated by the docs kit but changed since; "
                           "regenerate it with docs_kit.py scaffold --refresh instead of editing it")
        return want
    _, want_title = first_heading(want)
    lineno, got_title = first_heading(lines)
    if got_title != want_title:
        report.error("TITLE", rel, lineno, f"expected '{want_title}', found '{got_title}'")
    t_first, got = first_content_lines(want, 2), first_content_lines(lines, 2)
    if not got or got[0][1] != t_first[0][1]:
        report.error("NAV", rel, got[0][0] if got else None,
                     "navigation bar differs from the template; expected: " + t_first[0][1])
    problem = meta_problem(t_first[1][1], got[1][1] if len(got) > 1 else "") if len(t_first) > 1 else None
    placeholders = []
    if problem and problem[0] == "PLACEHOLDER":
        placeholders.append((got[1][0], problem[1]))
    elif problem:
        report.error(problem[0], rel, got[1][0] if len(got) > 1 else None, problem[1])
    if not tmpl.free_headings:
        want_h2, got_h2 = headings(want, 2), headings(lines, 2)
        if want_h2 != got_h2:
            missing = [h for h in want_h2 if h not in got_h2]
            extra = [h for h in got_h2 if h not in want_h2]
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"unexpected {extra}")
            report.error("HEADINGS", rel, None, "; ".join(detail) or "H2 headings out of order")
    placeholders += placeholder_findings(want_text, lines)
    if placeholders and lenient:
        tokens = sorted({m.group(1) for m in (re.match(r"placeholder (<.*>) not filled in", msg)
                                              for _, msg in placeholders) if m})
        report.warning("PLACEHOLDER", rel, placeholders[0][0],
                       f"{len(placeholders)} unfilled template item(s)"
                       + (f", e.g. {', '.join(sorted(tokens, key=len)[:3])}" if tokens else ""))
    else:
        for i, msg in placeholders:
            report.error("PLACEHOLDER", rel, i, msg)
    return want


def check_links(root, rel, template_lines, report, lenient):
    path = os.path.join(root, rel)
    base = os.path.dirname(path)
    lines = read_lines(path)
    checked = 0
    for lineno, target in relative_links(lines):
        checked += 1
        path_part, frag = split_target(target)
        dest = resolve(root, base, path_part) if path_part else path
        problem = None
        if not os.path.exists(dest):
            problem = ("LINK", f"{target} (not found)")
        elif frag and dest.endswith(".md") and os.path.isfile(dest):
            if frag.lower() not in anchors_for(dest) and not re.match(r"^L\d+", frag):
                problem = ("ANCHOR", f"{target} (no such heading)")
        if problem is None:
            continue
        unfilled = "<" in target or lines[lineno - 1] in template_lines
        if lenient and unfilled:
            report.warning(problem[0], rel, lineno, problem[1] + "; the line is still template text")
        else:
            report.error(problem[0], rel, lineno, problem[1])
    return checked


def linked_paths(root, rel):
    path = os.path.join(root, rel)
    out = set()
    for _, target in relative_links(read_lines(path), unused_definitions=False):
        part = split_target(target)[0]
        if part:
            dest = resolve(root, os.path.dirname(path), part)
            out.add(os.path.relpath(dest, root).replace(os.sep, "/"))
    return out


def standard_files(root, sets, all_links=False):
    """Relative paths of the documents whose links are checked."""
    out = []
    for ds in sets:
        directory = os.path.join(root, ds.docs_dir)
        if not os.path.isdir(directory):
            continue
        for current, subdirs, files in os.walk(directory):
            subdirs[:] = sorted(s for s in subdirs if s != "templates")
            for f in sorted(files):
                if f.endswith(".md") and (all_links or (current == directory and STANDARD_RE.match(f))):
                    out.append(os.path.relpath(os.path.join(current, f), root).replace(os.sep, "/"))
    return out


def compare_with_kit(root, cfg, kit_dir, report):
    vendor = os.path.join(root, VENDOR_DIR)
    stale = []
    for rel in kit_files(cfg["layout"], kit_dir):
        mine = os.path.join(vendor, rel)
        try:
            with open(mine, "rb") as a, open(os.path.join(kit_dir, rel), "rb") as b:
                if a.read() != b.read():
                    stale.append(rel)
        except OSError:
            stale.append(rel)
    if stale:
        report.notice("KIT", f"{VENDOR_DIR}/{CONFIG_FILE}", None,
                      f"{len(stale)} file(s) in {VENDOR_DIR}/ differ from the current docs kit "
                      f"({', '.join(stale[:3])}{', …' if len(stale) > 3 else ''}); run the Documentation "
                      "workflow with refresh to update them")


def run_check(root, cfg, report, all_links=False, lenient=False, kit_dir=None):
    vendor = os.path.join(root, VENDOR_DIR)
    sets = doc_sets(root, cfg, vendor)
    template_lines = {}
    for ds in sets:
        for tmpl in ds.templates:
            want = check_document(root, cfg, sets, ds, tmpl, report, lenient)
            if want is not None:
                template_lines[posixpath.join(ds.docs_dir, tmpl.name)] = {l for l in want if l.strip()}
    links = 0
    for rel in standard_files(root, sets, all_links):
        links += check_links(root, rel, template_lines.get(rel, set()), report, lenient)
    for rel in standard_files(root, sets):
        for lineno, msg in lint_mermaid(read_lines(os.path.join(root, rel))):
            report.error("MERMAID", rel, lineno, msg)
    root_readme = "docs/README.md"
    if cfg["layout"] == "monorepo" and os.path.isfile(os.path.join(root, root_readme)):
        linked = linked_paths(root, root_readme)
        for ds in sets[1:]:
            if f"{ds.docs_dir}/README.md" not in linked:
                report.error("UNLINKED", root_readme, None,
                             f"{ds.docs_dir}/README.md is not linked; add {ds.name} to the service tables")
    for ds in sets:
        readme = "README.md" if ds.base == "." else f"{ds.base}/README.md"
        if os.path.isfile(os.path.join(root, readme)) and \
                f"{ds.docs_dir}/README.md" not in linked_paths(root, readme):
            report.warning("README", readme, None, f"does not link to {ds.docs_dir}/README.md")
    if kit_dir and os.path.abspath(kit_dir) != os.path.abspath(vendor):
        compare_with_kit(root, cfg, kit_dir, report)
    return sum(len(ds.templates) for ds in sets), links


# --------------------------------------------------------------------------- Commands


def cmd_check(args):
    root = find_root(args.root)
    cfg = load_config(root)
    if cfg is None:
        msg = (f"{VENDOR_DIR}/{CONFIG_FILE} not found: this repository has not adopted the standard "
               "documentation. Run the Documentation workflow (or docs_kit.py scaffold) to add it.")
        if args.skip_if_missing:
            print(f"::warning title=docs not adopted::{msg}" if annotate() else f"WARNING {msg}")
            return 0
        print(msg, file=sys.stderr)
        return 1
    report = Report()
    docs, links = run_check(root, cfg, report, args.all_links, args.allow_placeholders, args.kit_dir)
    report.emit(annotate())
    headline = (f"docs-kit check: {report.count('error')} error(s), {report.count('warning')} warning(s); "
                f"{docs} standard documents and {links} relative links checked")
    print(headline)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(report.summary_markdown(headline))
    return 1 if report.count("error") else 0


def sync_file(src, dest, refresh):
    with open(src, "rb") as fh:
        data = fh.read()
    if os.path.exists(dest):
        with open(dest, "rb") as fh:
            if fh.read() == data:
                return "unchanged"
        if not refresh:
            return "kept (differs from the kit; refresh to replace)"
        action = "updated"
    else:
        action = "created"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(data)
    if dest.endswith(".py"):
        os.chmod(dest, 0o755)
    return action


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def cmd_scaffold(args):
    root = find_root(args.root)
    vendor = os.path.join(root, VENDOR_DIR)
    existing = load_config(root)
    cfg = dict(existing or DEFAULTS)
    for key in ("name", "repository", "components_dir", "branch"):
        if getattr(args, key):
            cfg[key] = getattr(args, key)
    if args.layout and args.layout != "auto":
        cfg["layout"] = args.layout
    elif args.layout == "auto" or not cfg["layout"]:
        cfg["layout"] = detect_layout(root, cfg)
    if cfg["layout"] not in LAYOUTS:
        raise KitError(f"layout must be one of {', '.join(LAYOUTS)}")
    cfg["repository"] = cfg["repository"] or detect_repository(root)
    cfg["name"] = cfg["name"] or cfg["repository"].split("/")[-1]

    results = []
    kit_dir = os.path.abspath(args.kit_dir or KIT_DIR)
    if kit_dir != os.path.abspath(vendor):
        for rel in kit_files(cfg["layout"], kit_dir):
            action = sync_file(os.path.join(kit_dir, rel), os.path.join(vendor, rel), args.refresh)
            results.append((f"{VENDOR_DIR}/{rel}", action))
    config_text = json.dumps({k: cfg[k] for k in DEFAULTS}, indent=2) + "\n"
    config_path = os.path.join(vendor, CONFIG_FILE)
    if existing is None:
        write_text(config_path, config_text)
        results.append((f"{VENDOR_DIR}/{CONFIG_FILE}", "created"))
    elif {k: existing[k] for k in DEFAULTS} != {k: cfg[k] for k in DEFAULTS}:
        write_text(config_path, config_text)
        results.append((f"{VENDOR_DIR}/{CONFIG_FILE}", "updated"))

    sets = doc_sets(root, cfg, vendor)
    for ds in sets:
        for tmpl in ds.templates:
            rel = posixpath.join(ds.docs_dir, tmpl.name)
            path = os.path.join(root, rel)
            text = render(tmpl, context(cfg, ds, sets, tmpl.name), cfg["layout"])
            if not os.path.exists(path):
                write_text(path, text)
                results.append((rel, "created"))
            elif tmpl.managed:
                with open(path, encoding="utf-8") as fh:
                    same = fh.read() == text
                if same:
                    results.append((rel, "unchanged"))
                elif args.refresh:
                    write_text(path, text)
                    results.append((rel, "updated"))
                else:
                    results.append((rel, "kept (differs from the kit; refresh to replace)"))
            else:
                results.append((rel, "kept (already exists)"))

    changed = [r for r in results if r[1] in ("created", "updated")]
    lines = [
        f"Layout **{cfg['layout']}**"
        + (f" with services under `{cfg['components_dir']}/`" if cfg["layout"] == "monorepo" else "")
        + f"; {len(sets)} documentation set(s); {len(changed)} file(s) created or updated.",
        "",
        "| File | Result |",
        "|---|---|",
    ]
    lines += [f"| `{rel}` | {action} |" for rel, action in results if action != "unchanged"]
    summary = "\n".join(lines) + "\n"
    print(summary)
    if args.summary:
        write_text(os.path.abspath(args.summary), summary)
    return 0


def cmd_list(args):
    root = find_root(args.root)
    cfg = load_config(root)
    if cfg is None:
        return 0
    files = standard_files(root, doc_sets(root, cfg, os.path.join(root, VENDOR_DIR)))
    if args.changed_since:
        out = subprocess.run(["git", "-C", root, "diff", "--name-only", "--diff-filter=d",
                              f"{args.changed_since}...HEAD"], capture_output=True, text=True, check=True)
        changed = set(out.stdout.split("\n"))
        files = [f for f in files if f in changed]
    if args.mermaid:
        files = [f for f in files if mermaid_blocks(read_lines(os.path.join(root, f)))]
    for f in files:
        print(f)
    return 0


def cmd_mermaid_source(args):
    """Write the visible Mermaid blocks of a document to a file for the Mermaid CLI."""
    blocks = mermaid_blocks(read_lines(args.source))
    text = "".join("```mermaid\n" + "\n".join(l for _, l in body) + "\n```\n\n" for _, body in blocks)
    write_text(os.path.abspath(args.dest), text)
    return 0


def annotate():
    return os.environ.get("GITHUB_ACTIONS") == "true"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="repository root (default: found from this script or git)")
    sub = ap.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="check structure, placeholders, links and diagrams")
    c.add_argument("--all-links", action="store_true", help="also check links in other Markdown under the docs folders")
    c.add_argument("--allow-placeholders", action="store_true",
                   help="report unfilled template text as warnings instead of errors")
    c.add_argument("--skip-if-missing", action="store_true",
                   help="succeed with a warning when the repository has no docs/templates/docs-kit.json")
    c.add_argument("--kit-dir", help="a docs kit to compare docs/templates/ with (reports a notice when they differ)")

    s = sub.add_parser("scaffold", help="add missing documents and the kit files under docs/templates/")
    s.add_argument("--layout", choices=LAYOUTS + ("auto",), help="single or monorepo (default: keep, else detect)")
    s.add_argument("--name", help="name used in root document titles (default: repository name)")
    s.add_argument("--repository", help="owner/repo (default: from GITHUB_REPOSITORY or the git remote)")
    s.add_argument("--components-dir", dest="components_dir", help="monorepo services directory (default: services)")
    s.add_argument("--branch", help="branch named in metadata lines (default: dev)")
    s.add_argument("--refresh", action="store_true",
                   help="also replace kit-managed files (templates, this script, documentation standards)")
    s.add_argument("--kit-dir", help="kit to copy templates from (default: this script's directory)")
    s.add_argument("--summary", help="also write the Markdown summary to this file")

    l = sub.add_parser("list", help="print the standard documents")
    l.add_argument("--changed-since", help="only documents changed between this commit and HEAD")
    l.add_argument("--mermaid", action="store_true", help="only documents that contain Mermaid diagrams")

    m = sub.add_parser("mermaid-source", help="write a document's visible Mermaid blocks to a file")
    m.add_argument("source")
    m.add_argument("dest")

    args = ap.parse_args(argv)
    try:
        return {"check": cmd_check, "scaffold": cmd_scaffold, "list": cmd_list,
                "mermaid-source": cmd_mermaid_source}[args.command](args)
    except KitError as exc:
        print(f"docs-kit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
