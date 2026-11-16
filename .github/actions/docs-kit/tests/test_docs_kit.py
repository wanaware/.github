"""Tests for docs_kit.py.

Run from the repository root:

    python3 -m unittest discover -s .github/actions/docs-kit/tests -v
"""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True  # keep __pycache__ out of the kit directory, which repositories copy from
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("docs_kit", os.path.join(KIT, "docs_kit.py"))
dk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dk)


def visible(text):
    """Line numbers that outside_fences reports as ordinary content."""
    return [n for n, _ in dk.outside_fences(text.split("\n"))]


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = dk.main(list(argv))
    return code, out.getvalue()


def fill(text):
    """Do what an author does to a scaffolded page: fill every placeholder, including those
    that wrap onto several lines, and drop the comments."""
    text = dk.COMMENT_RE.sub("", text)
    text = text.replace(dk.DATE_TOKEN, "2026-11-16").replace(dk.SHA_TOKEN, "abc1234")
    return dk.ANGLE_RE.sub(lambda m: "filled" if dk.is_placeholder(m.group(0)) else m.group(0), text)


class OutsideFencesTest(unittest.TestCase):
    """Ported from asset-pipeline scripts/test_check_docs.py."""

    def test_simple_fence_is_skipped(self):
        self.assertEqual(visible("before\n```bash\ncode\n```\nafter"), [1, 5])

    def test_four_backtick_fence_contains_three_backtick_fences(self):
        text = "\n".join(["intro", "````markdown", "## Example heading", "```mermaid", "flowchart LR",
                          "```", "[link](missing.md)", "````", "## Real heading"])
        self.assertEqual(visible(text), [1, 9])

    def test_closing_fence_must_use_the_same_character(self):
        self.assertEqual(visible("~~~\n```\nstill code\n~~~\nafter"), [5])

    def test_line_with_text_after_fence_does_not_close(self):
        self.assertEqual(visible("```\n``` not a closing fence\n```\nafter"), [4])

    def test_fence_indented_under_a_list_item_is_skipped(self):
        text = "\n".join(["10. Example:", "", "    ```markdown", "    [link](missing.md)", "    ```", "after"])
        self.assertEqual(visible(text), [1, 2, 6])

    def test_backtick_run_with_backticks_after_it_is_inline_code(self):
        self.assertEqual(visible("``` `inline` ```\n[link](a.md)\nafter"), [1, 2, 3])

    def test_tilde_fence_may_contain_backticks_in_its_info_string(self):
        self.assertEqual(visible("~~~ aa ``` ~~~\ncode\n~~~\nafter"), [4])

    def test_indented_sample_outside_a_list_is_not_a_fence(self):
        text = "\n".join(["Syntax:", "", "    ```markdown", "", "See [real](real.md).", "## Real heading"])
        self.assertEqual(visible(text), [1, 2, 3, 4, 5, 6])
        self.assertEqual(dk.headings(text.split("\n"), 2), ["Real heading"])

    def test_fence_in_a_nested_list_item_is_skipped(self):
        text = "\n".join(["- outer", "  - inner", "", "      ```", "      [x](missing.md)", "      ```", "after"])
        self.assertEqual(visible(text), [1, 2, 3, 7])

    def test_fence_in_a_compact_nested_list_item_is_skipped(self):
        for marker, indent in (("- - ", 6), ("1. - ", 7)):
            with self.subTest(marker=marker):
                pad = " " * indent
                text = "\n".join([marker + "Example:", "", pad + "```", pad + "[x](missing.md)", pad + "```", "after"])
                self.assertEqual(visible(text), [1, 2, 6])

    def test_list_ends_before_indented_code(self):
        self.assertEqual(visible("- item\n\nParagraph.\n\n    ```\n    code\nafter"), [1, 2, 3, 4, 5, 6, 7])

    def test_closing_fence_indented_four_spaces_does_not_close(self):
        self.assertEqual(visible("```\n    ```\ncode\n```\nafter"), [5])

    def test_headings_inside_examples_are_not_anchors(self):
        lines = ["# Title", "````markdown", "## Hidden", "```", "````", "## Shown"]
        self.assertEqual(dk.headings(lines, 2), ["Shown"])


class MarkdownHelpersTest(unittest.TestCase):
    def test_mermaid_blocks_are_split_even_when_adjacent(self):
        lines = ["```mermaid", "flowchart LR", "```", "```mermaid", "sequenceDiagram", "```", "```bash", "x", "```"]
        blocks = dk.mermaid_blocks(lines)
        self.assertEqual([(start, [l for _, l in body]) for start, body in blocks],
                         [(1, ["flowchart LR"]), (4, ["sequenceDiagram"])])

    def test_prose_drops_comments_and_inline_code(self):
        lines = ["a <!-- one", "two --> b `<code>` c", "```", "<fenced>", "```"]
        self.assertEqual(list(dk.prose(lines)), [(1, "a "), (2, " b  c")])

    def test_placeholders_exclude_html_tags_and_autolinks(self):
        for token in ("<br/>", "<br>", "<a name=\"x\">", "</td>", "<https://example.com>", "<!-- c -->"):
            self.assertFalse(dk.is_placeholder(token), token)
        for token in ("<one line>", "<service>", "<name>", "<a placeholder>"):
            self.assertTrue(dk.is_placeholder(token), token)

    def test_mermaid_stroke_colours_are_rejected_but_widths_and_dashes_are_not(self):
        doc = "\n".join(["```mermaid", "flowchart LR", "  a --> b",
                          "  classDef focus stroke:#ffffff", "  classDef ok stroke-width:3px",
                          "  classDef ext stroke-dasharray:4 3", "  classDef bg background-color:#000", "```"])
        found = dk.lint_mermaid(doc.split("\n"))
        self.assertEqual([line for line, _ in found], [4, 7])

    def test_double_backtick_code_spans_hide_their_contents(self):
        line = "Write `` [sample](missing.md) `` or `[x](y.md)`, but [real](real.md) is a link."
        self.assertEqual([t for _, t in dk.relative_links([line])], ["real.md"])

    def test_headings_github_renders(self):
        lines = [
            "Title", "=====", "",                      # 1  Setext H1
            "Section `code`", "--------------", "",    # 4  Setext H2 (code kept for the slug)
            "## ATX section", "",                      # 7
            "Text before a rule.", "", "---", "",      # a rule after a blank line, not a heading
            "- item", "---", "",                       # a rule after a list, not a heading
            "<!--", "## Hidden", "-->", "",            # commented out
            "```", "## Fenced", "```",                 # code
        ]
        self.assertEqual(dk.heading_list(lines),
                         [(1, 1, "Title"), (4, 2, "Section `code`"), (7, 2, "ATX section")])
        self.assertEqual(dk.headings(lines, 2), ["Section `code`", "ATX section"])

    def test_anchors_match_github(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "a.md")
        with open(path, "w") as fh:
            fh.write("## Foo\n\n## Foo\n\n## Foo 1\n\nIntro.\n\n  ## Indented\n\n> ## Quoted\n")
        dk._anchor_cache.clear()
        self.assertEqual(sorted(dk.anchors_for(path)), ["foo", "foo-1", "foo-1-1", "indented", "quoted"])
        # Indented and quoted headings get anchors but are not the document's own sections.
        with open(path) as fh:
            self.assertEqual(dk.headings(fh.read().split("\n"), 2), ["Foo", "Foo", "Foo 1"])

    def test_stray_comment_markers_inside_paragraphs_are_text(self):
        links = lambda lines: [t for _, t in dk.relative_links(lines)]
        self.assertEqual(links(["Use a <!-- marker.", "", "See [x](x.md)."]), ["x.md"])
        self.assertEqual(links(["A <!-- comment", "that closes --> then [y](y.md)."]), ["y.md"])
        self.assertEqual(links(["<!-- a block comment that never closes", "", "[z](z.md)"]), [])

    def test_unused_reference_definitions_do_not_count_as_service_links(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "README.md"), "w") as fh:
            fh.write("[A][a], [b][], [C].\n\n[a]: a.md\n[b]: b.md\n[c]: c.md\n[unused]: d.md\n")
        self.assertEqual(sorted(dk.linked_paths(d, "README.md")), ["a.md", "b.md", "c.md"])
        with open(os.path.join(d, "README.md"), "w") as fh:
            fh.write("See the [Alpha\ndocs] page.\n\n[Alpha docs]: alpha.md\n")
        self.assertEqual(sorted(dk.linked_paths(d, "README.md")), ["alpha.md"])

    def test_headings_in_code_inside_block_quotes_are_not_anchors(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "a.md")
        with open(path, "w") as fh:
            fh.write("> Example:\n>\n> ```markdown\n> ## Hidden\n> ```\n\n> ## Shown\n>\n> > ### Deeper\n")
        dk._anchor_cache.clear()
        self.assertEqual(sorted(dk.anchors_for(path)), ["deeper", "shown"])

    def test_definitions_are_not_setext_headings(self):
        lines = ["Intro.", "", "[guide]: README.md", "---", "", "[^1]: A footnote.", "---", "",
                 "[ref]: x.md", "Real title", "=========="]
        self.assertEqual(dk.heading_list(lines), [(10, 1, "Real title")])
        # Text that only looks like a definition is a paragraph, so it can be underlined.
        self.assertEqual(dk.heading_list(["[Status]: not yet implemented", "==="]),
                         [(1, 1, "[Status]: not yet implemented")])

    def test_links_that_wrap_onto_the_next_line(self):
        links = lambda lines: [(n, t) for n, t in dk.relative_links(lines)]
        self.assertEqual(links(["See the [architecture", "guide](a.md) and [b](", "b.md)."]),
                         [(1, "a.md"), (2, "b.md")])
        self.assertEqual(links(["![a diagram of", "the flow](flow.png)"]), [(1, "flow.png")])
        # Destinations keep their spaces exactly (a file name may contain two).
        self.assertEqual(links(["[d](<images/system  overview.png>)"]), [(1, "images/system  overview.png")])
        # A line break between "]" and "(" ends the link text: not a link, as on GitHub.
        self.assertEqual(links(["See [the guide]", "(missing.md)."]), [])
        # Brackets in different paragraphs never form a link.
        self.assertEqual(links(["An open [bracket.", "", "Later](x.md)"]), [])

    def test_code_inside_block_quotes_and_protocol_relative_urls_are_not_relative_links(self):
        lines = ["> ```markdown", "> [example](missing.md)", "> ```", "", "> See [real](real.md).",
                 "", "[site](//example.com/page)"]
        self.assertEqual([t for _, t in dk.relative_links(lines)], ["real.md"])

    def test_commented_out_diagrams_are_neither_linted_nor_rendered(self):
        lines = ["<!--", "```mermaid", "graph TD", "```", "-->", "", "```mermaid", "flowchart LR", "  a --> b", "```"]
        self.assertEqual(dk.lint_mermaid(lines), [])
        self.assertEqual([start for start, _ in dk.mermaid_blocks(lines)], [7])
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        src, dest = os.path.join(d, "a.md"), os.path.join(d, "out", "a.md")
        with open(src, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        self.assertEqual(run("mermaid-source", src, dest)[0], 0)
        with open(dest) as fh:
            self.assertEqual(fh.read(), "```mermaid\nflowchart LR\n  a --> b\n```\n\n")

    def test_fences_inside_html_comments_are_not_fences(self):
        # An unclosed fence inside a comment neither crashes nor hides the rest of the document.
        lines = ["<!--", "```mermaid", "graph TD", "-->", "", "[x](x.md)", "", "```mermaid", "graph LR", "```"]
        self.assertEqual([t for _, t in dk.relative_links(lines)], ["x.md"])
        self.assertEqual([line for line, _ in dk.lint_mermaid(lines)], [9])
        # A stray mid-line "<!--" is text: it does not hide later diagrams.
        self.assertEqual([line for line, _ in dk.lint_mermaid(["Use a <!-- marker.", "", "```mermaid", "graph TD", "```"])], [4])
        # Comment markers inside a real code block are code.
        self.assertEqual(visible("```html\n<!-- a\n```\nafter"), [4])

    def test_links_inside_html_comments_are_not_checked(self):
        lines = ["Text.", "<!--", "[old]: missing.md", "An old [inline](gone.md) link.", "-->",
                 "<!-- [x](hidden.md) --> but [shown](real.md)", "[live]: live.md"]
        self.assertEqual([t for _, t in dk.relative_links(lines)], ["real.md", "live.md"])

    def test_comment_markers_in_code_spans_do_not_open_comments(self):
        lines = ["Write `<!--` to start a comment.", "See [arch](missing.md).", "",
                 "`<!--` and `-->` mark a comment, so <!-- [hidden](h.md) --> [shown](s.md)."]
        self.assertEqual([t for _, t in dk.relative_links(lines)], ["missing.md", "s.md"])
        self.assertEqual(list(dk.prose(["a `<!--` b <!-- c --> e `x` f"])), [(1, "a  b  e  f")])
        # Inside a comment there are no code spans: the comment ends at the first -->, as in HTML.
        self.assertEqual(list(dk.prose(["<!-- c `-->` d"])), [(1, "` d")])

    def test_link_destinations(self):
        lines = ["[a](../schema(v2).graphql) [b](<path with spaces.md>) [c](x.md \"title\")",
                 "[ref]: ../defs.md \"title\"", "[^1]: a footnote, not a link", "[e](https://example.com)"]
        self.assertEqual([t for _, t in dk.relative_links(lines)],
                         ["../schema(v2).graphql", "path with spaces.md", "x.md", "../defs.md"])
        self.assertEqual(dk.split_target("../a%20b.md?raw=1#caf%C3%A9"), ("../a b.md", "café"))

    def test_mermaid_lint(self):
        doc = "\n".join([
            "```mermaid", "graph TD", "  a --> b", "```",
            "```mermaid", "sequenceDiagram", "  A->>B: hi", "```",
            "```mermaid", "flowchart LR", "  style a fill:#f00", "  classDef x fill:#fff", "```",
            "```mermaid", "%%{init: {}}%%", "flowchart LR", "```",
            "```mermaid", "sequenceDiagram", "  autonumber", "  A->>B: ok", "```",
        ])
        messages = [m for _, m in dk.lint_mermaid(doc.split("\n"))]
        self.assertTrue(any("'graph' is not allowed" in m for m in messages))
        self.assertTrue(any("autonumber" in m for m in messages))
        self.assertTrue(any("'style'" in m for m in messages))
        self.assertTrue(any("classDef must not set colours" in m for m in messages))
        self.assertTrue(any("%%{init}%%" in m for m in messages))
        self.assertEqual(len(messages), 5)


class RenderTest(unittest.TestCase):
    def template(self, body, front='<!-- docs-kit: nav="Data model" managed -->'):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "02-data-model.md")
        with open(path, "w") as fh:
            fh.write(front + "\n" + body)
        return dk.Template(path)

    def ctx(self, **kw):
        base = {"NAME": "svc", "DOCS_ROOT": "../../../docs", "ROOT": "../../.."}
        base.update(kw)
        return base

    def test_front_matter(self):
        t = self.template("# x\n")
        self.assertEqual((t.nav, t.managed, t.free_headings), ("Data model", True, False))
        self.assertEqual(t.body, "# x\n")

    def test_block_and_inline_conditionals(self):
        body = "a{{#single}} S{{/single}}{{#monorepo}} M{{/monorepo}}\n{{#single}}\nonly single\n{{/single}}\nend"
        t = self.template(body)
        self.assertEqual(dk.render(t, self.ctx(), "single"), "a S\nonly single\nend\n")
        self.assertEqual(dk.render(t, self.ctx(), "monorepo"), "a M\nend\n")

    def test_tokens_and_docs_root(self):
        t = self.template("# {{NAME}}\n[s]({{DOCS_ROOT}}/10-x.md)")
        self.assertEqual(dk.render(t, self.ctx(), "monorepo"), "# svc\n[s](../../../docs/10-x.md)\n")
        self.assertEqual(dk.render(t, self.ctx(DOCS_ROOT="."), "single"), "# svc\n[s](10-x.md)\n")

    def test_mermaid_hexagons_are_not_tokens(self):
        t = self.template('in{{"STREAM<br/>subject"}} --> svc')
        self.assertEqual(dk.render(t, self.ctx(), "single"), 'in{{"STREAM<br/>subject"}} --> svc\n')

    def test_unknown_token_and_unbalanced_blocks_fail(self):
        for body in ("{{NOPE}}", "{{#single}}\nx", "{{/single}}", "{{#single}}\n{{/monorepo}}"):
            with self.subTest(body=body), self.assertRaises(dk.KitError):
                dk.render(self.template(body), self.ctx(), "single")


class KitTemplatesTest(unittest.TestCase):
    """The kit's own templates must be well-formed for both layouts."""

    def test_every_template_has_front_matter_and_known_tokens(self):
        for s in dk.TEMPLATE_SETS:
            for t in dk.load_templates(os.path.join(KIT, s)):
                with self.subTest(template=f"{s}/{t.name}"):
                    with open(t.path) as fh:
                        self.assertTrue(dk.FRONT_RE.match(fh.readline()), "missing docs-kit front matter")
                    self.assertTrue(t.body.startswith("# {{NAME}}: "))

    def test_numbered_headings(self):
        for s in ("component", "platform"):
            for t in dk.load_templates(os.path.join(KIT, s)):
                with self.subTest(template=f"{s}/{t.name}"):
                    h2 = dk.headings(t.body.split("\n"), 2)
                    self.assertTrue(h2)
                    self.assertEqual([h.split(". ")[0] for h in h2], [str(i) for i in range(1, len(h2) + 1)])

    def test_sets_have_the_same_files(self):
        names = lambda s: [t.name for t in dk.load_templates(os.path.join(KIT, s))]
        self.assertEqual(names("component"), names("platform"))
        self.assertEqual(names("shared"), ["09-glossary.md", "10-documentation-standards.md"])


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        dk._anchor_cache.clear()
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.write("README.md", "# repo\n\nSee [the documentation](docs/README.md).\n")

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text):
        os.makedirs(os.path.dirname(self.path(rel)) or ".", exist_ok=True)
        with open(self.path(rel), "w") as fh:
            fh.write(text)

    def read(self, rel):
        with open(self.path(rel)) as fh:
            return fh.read()

    def scaffold(self, *extra):
        code, out = run("--root", self.root, "scaffold", "--repository", "wanaware/example", *extra)
        self.assertEqual(code, 0, out)
        return out

    def check(self, lenient=False):
        dk._anchor_cache.clear()
        report = dk.Report()
        dk.run_check(self.root, dk.load_config(self.root), report, lenient=lenient)
        return report

    def errors(self, report):
        return [(code, path) for level, code, path, _, _ in report.items if level == "error"]

    def fill_all(self):
        for current, _, files in os.walk(self.root):
            if os.sep + "templates" in current:
                continue
            for f in files:
                p = os.path.join(current, f)
                if f.endswith(".md") and dk.STANDARD_RE.match(f) and "10-documentation" not in f:
                    with open(p) as fh:
                        text = fh.read()
                    with open(p, "w") as fh:
                        fh.write(fill(text))


class SingleLayoutTest(RepoTestCase):
    def test_scaffold_creates_the_set_and_vendors_the_kit(self):
        self.scaffold()
        cfg = dk.load_config(self.root)
        self.assertEqual((cfg["layout"], cfg["name"], cfg["repository"]), ("single", "example", "wanaware/example"))
        for name in ["README.md"] + [f"0{i}-" for i in range(1, 9)]:
            self.assertTrue(any(f.startswith(name) for f in os.listdir(self.path("docs"))), name)
        self.assertTrue(os.path.isfile(self.path("docs/09-glossary.md")))
        self.assertTrue(os.access(self.path("docs/templates/docs_kit.py"), os.X_OK))
        self.assertFalse(os.path.exists(self.path("docs/templates/platform")))
        readme = self.read("docs/README.md").split("\n")
        self.assertEqual(readme[0], "# example: Overview")
        self.assertTrue(readme[2].startswith("**Overview** · [Architecture](01-architecture.md)"))
        self.assertTrue(readme[2].endswith("[Glossary](09-glossary.md) · [Standards](10-documentation-standards.md)"))
        self.assertTrue(readme[4].startswith("> **Repository:** `wanaware/example` · **Last verified against source:**"))

    def test_fresh_scaffold_fails_strict_only_on_placeholders_and_passes_lenient(self):
        self.scaffold()
        strict = self.check()
        self.assertTrue(strict.count("error"))
        self.assertEqual({code for code, _ in self.errors(strict)}, {"PLACEHOLDER"})
        self.assertEqual(self.errors(self.check(lenient=True)), [])

    def test_filled_documents_pass_strict(self):
        self.scaffold()
        self.fill_all()
        report = self.check()
        self.assertEqual(self.errors(report), [], report.items)
        self.assertEqual(report.count("warning"), 0, report.items)

    def test_scaffold_never_overwrites_and_refresh_replaces_managed_files(self):
        self.scaffold()
        self.write("docs/01-architecture.md", "mine\n")
        self.write("docs/10-documentation-standards.md", "edited\n")
        self.write("docs/templates/component/05-api.md", "custom\n")
        out = self.scaffold()
        self.assertIn("kept (differs from the kit", out)
        self.assertEqual(self.read("docs/01-architecture.md"), "mine\n")
        self.assertEqual(self.read("docs/10-documentation-standards.md"), "edited\n")
        self.assertEqual(self.read("docs/templates/component/05-api.md"), "custom\n")
        self.scaffold("--refresh")
        self.assertEqual(self.read("docs/01-architecture.md"), "mine\n")
        self.assertIn("Documentation Standards", self.read("docs/10-documentation-standards.md"))
        self.assertIn("API Reference", self.read("docs/templates/component/05-api.md"))

    def test_check_reports_structural_problems(self):
        self.scaffold()
        self.fill_all()
        os.remove(self.path("docs/02-data-model.md"))
        arch = self.read("docs/01-architecture.md")
        arch = arch.replace("# example: Architecture", "# Example: Architecture")
        arch = arch.replace("## 5. Concurrency and scaling model", "## 5. Scaling")
        arch = arch.replace("**Architecture** · ", "Architecture · ")
        arch += "\n[gone](missing.md) [bad anchor](README.md#no-such-heading) [ok](README.md#1-at-a-glance)\n"
        arch += "\n```mermaid\nsequenceDiagram\n  A->>B: hi\n```\n"
        self.write("docs/01-architecture.md", arch)
        self.write("docs/03-messaging.md", self.read("docs/03-messaging.md").replace(
            "2026-11-16", "YYYY-MM-DD"))
        codes = sorted({code for code, _ in self.errors(self.check())})
        self.assertEqual(codes, ["ANCHOR", "HEADINGS", "LINK", "MERMAID", "MISSING", "NAV", "PLACEHOLDER", "TITLE"])

    def test_managed_document_edits_are_reported_as_stale(self):
        self.scaffold()
        self.fill_all()
        self.write("docs/10-documentation-standards.md", self.read("docs/10-documentation-standards.md") + "x\n")
        report = self.check()
        self.assertEqual(self.errors(report), [])
        self.assertIn("STALE", [code for _, code, _, _, _ in report.items])

    def test_placeholders_that_wrap_onto_several_lines_are_reported(self):
        self.scaffold()
        template = self.read("docs/01-architecture.md")
        wrapped = re.search(r"<Architectural style[^>]*>", template).group(0)
        self.assertIn("\n", wrapped)  # the template wraps it onto two lines
        self.fill_all()
        arch = self.read("docs/01-architecture.md")
        for leftover in (wrapped, " ".join(wrapped.split())):  # as scaffolded, and re-wrapped
            with self.subTest(leftover=leftover[:30]):
                self.write("docs/01-architecture.md", arch.replace("## 2. System context",
                                                                    leftover + "\n\n## 2. System context"))
                found = [(code, line) for level, code, path, line, msg in self.check().items
                         if level == "error" and path == "docs/01-architecture.md"]
                self.assertEqual([code for code, _ in found], ["PLACEHOLDER"])
                lines = self.read("docs/01-architecture.md").split("\n")
                self.assertTrue(lines[found[0][1] - 1].startswith("<Architectural style"))

    def test_angle_brackets_in_different_paragraphs_are_not_a_placeholder(self):
        self.assertFalse(dk.is_placeholder("< 5 items.\n\nThen more than >"))
        self.assertEqual(list(dk.placeholder_tokens(["a <wrapped", "placeholder> b", "", "x < y", "", "z > w"])),
                         [(1, "<wrapped placeholder>")])

    def test_links_resolve_with_parentheses_queries_encoded_fragments_and_references(self):
        self.scaffold()
        self.fill_all()
        self.write("schema(v2).graphql", "type Query\n")
        self.write("docs/01-architecture.md", self.read("docs/01-architecture.md") + "\n".join([
            "", "### Café", "",
            "[s](../schema(v2).graphql) [raw](../schema(v2).graphql?raw=1) [c](#caf%C3%A9) [d][defs]",
            "Literal example: `` [sample](missing.md) ``", "", "[defs]: 02-data-model.md#1-overview", ""]))
        self.assertEqual(self.errors(self.check()), [])
        self.write("docs/01-architecture.md", self.read("docs/01-architecture.md") + "\n[gone]: ../missing.yaml\n")
        self.assertEqual(self.errors(self.check()), [("LINK", "docs/01-architecture.md")])

    def test_setext_anchors_root_relative_links_and_commented_headings(self):
        self.scaffold()
        self.fill_all()
        self.write("README.md", "Example\n=======\n\n[Documentation](docs/README.md)\n\nSetup\n-----\n\n## Setup\n")
        arch = self.read("docs/01-architecture.md")
        self.write("docs/01-architecture.md", arch + "\n".join([
            "", "[a](../README.md#example) [b](../README.md#setup) [c](../README.md#setup-1) [d](/README.md#setup)", ""]))
        self.assertEqual(self.errors(self.check()), [])
        self.write("docs/01-architecture.md", arch + "\n".join([
            "", "<!--", "## Hidden section", "-->", "", "[h](#hidden-section) [m](/missing.md)", ""]))
        self.assertEqual(sorted(code for code, _ in self.errors(self.check())), ["ANCHOR", "LINK"])

    def test_impossible_dates_fail(self):
        self.scaffold()
        self.fill_all()
        for date in ("2026-02-31", "2026-99-99"):
            with self.subTest(date=date):
                text = self.read("docs/02-data-model.md")
                self.write("docs/02-data-model.md", re.sub(r"\d{4}-\d{2}-\d{2}", date, text, count=1))
                self.assertEqual(self.errors(self.check()), [("META", "docs/02-data-model.md")])

    def test_template_placeholders_in_code_blocks_are_reported(self):
        self.scaffold()
        template = self.read("docs/08-development.md")
        self.assertIn("<entry points>", template)
        self.fill_all()
        filled = self.read("docs/08-development.md")
        self.write("docs/08-development.md", filled.replace("cmd/            filled", "cmd/            <entry points>"))
        found = [(code, msg) for level, code, path, _, msg in self.check().items if level == "error"]
        self.assertEqual(found, [("PLACEHOLDER", "placeholder <entry points> not filled in (in a code block)")])
        # A document's own <angle> examples in code are not template text.
        self.write("docs/08-development.md", filled + "\n```bash\ncd services/<service>\n```\n")
        self.assertEqual(self.errors(self.check()), [])

    def test_check_without_adoption(self):
        code, out = run("--root", self.root, "check")
        self.assertEqual(code, 1)
        self.assertIn("not adopted", out)
        code, out = run("--root", self.root, "check", "--skip-if-missing")
        self.assertEqual(code, 0)

    def test_vendored_copy_runs_on_its_own(self):
        self.scaffold()
        self.fill_all()
        out = subprocess.run(["python3", self.path("docs/templates/docs_kit.py"), "check"],
                             capture_output=True, text=True, env={**os.environ, "GITHUB_ACTIONS": ""})
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("0 error(s)", out.stdout)


class MonorepoLayoutTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        for svc in ("alpha", "beta"):
            self.write(f"services/{svc}/README.md", f"# {svc}\n\n[Documentation](docs/README.md)\n")

    def test_layout_is_detected_and_every_service_gets_a_set(self):
        self.scaffold("--name", "Example Platform")
        self.assertEqual(dk.load_config(self.root)["layout"], "monorepo")
        alpha = self.read("services/alpha/docs/03-messaging.md").split("\n")
        self.assertEqual(alpha[0], "# alpha: Messaging")
        self.assertTrue(alpha[2].endswith("[Development](08-development.md) · [Platform docs](../../../docs/README.md)"))
        self.assertTrue(alpha[4].startswith("> **Service:** `services/alpha` · **Last verified against source:**"))
        root = self.read("docs/README.md")
        self.assertIn("# Example Platform: Overview", root)
        self.assertIn("> **Scope:** all services in this monorepo", root)
        self.assertIn("[docs](../services/beta/docs/README.md)", root)
        self.assertIn("[03](../services/alpha/docs/03-messaging.md)", root)

    def test_filled_documents_pass_strict(self):
        self.scaffold()
        self.fill_all()
        report = self.check()
        self.assertEqual(self.errors(report), [], report.items)

    def test_new_service_must_be_scaffolded_and_linked(self):
        self.scaffold()
        self.fill_all()
        self.write("services/gamma/README.md", "# gamma\n\n[Documentation](docs/README.md)\n")
        codes = {code for code, _ in self.errors(self.check())}
        self.assertEqual(codes, {"MISSING", "UNLINKED"})
        self.scaffold()  # adds gamma's docs; docs/README.md exists, so it is not rewritten
        self.fill_all()
        self.assertEqual({code for code, _ in self.errors(self.check())}, {"UNLINKED"})

    def test_services_linked_through_reference_definitions_count(self):
        self.scaffold()
        self.fill_all()
        readme = self.read("docs/README.md")
        for label in ("docs", "README"):
            readme = readme.replace(f"[{label}](../services/alpha/docs/README.md)", f"[{label}][alpha]")
        self.assertNotIn("(../services/alpha/docs/README.md)", readme)
        self.write("docs/README.md", readme + "\n[alpha]: ../services/alpha/docs/README.md\n")
        self.assertEqual(self.errors(self.check()), [])

    def test_excluded_directories_are_skipped(self):
        self.scaffold()
        cfg_path = self.path("docs/templates/docs-kit.json")
        self.write(cfg_path, self.read(cfg_path).replace('"exclude": []', '"exclude": ["beta"]'))
        self.scaffold()
        self.assertEqual([s.name for s in dk.doc_sets(self.root, dk.load_config(self.root),
                                                      self.path("docs/templates"))], ["example", "alpha"])

    def test_list_changed_documents_with_diagrams(self):
        self.scaffold()
        git = lambda *a: subprocess.run(["git", "-C", self.root, *a], check=True, capture_output=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "base")
        self.write("services/alpha/docs/03-messaging.md", self.read("services/alpha/docs/03-messaging.md") + "\nmore\n")
        self.write("services/alpha/docs/05-api.md", self.read("services/alpha/docs/05-api.md") + "\nmore\n")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qam", "change")
        code, out = run("--root", self.root, "list", "--mermaid", "--changed-since", "HEAD~1")
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["services/alpha/docs/03-messaging.md"])


if __name__ == "__main__":
    unittest.main()
