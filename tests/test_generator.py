"""Tests for the generator module."""

from textwrap import dedent

import pytest

from mdxify.generator import generate_mdx, is_module_empty
from mdxify.parser import parse_module_fast
from mdxify.renderers import MarkdownRenderer, MDXRenderer


@pytest.mark.parametrize("renderer", [MDXRenderer(), MarkdownRenderer()], ids=["mdx", "md"])
def test_generate_property_and_method_kinds(tmp_path, renderer):
    source = tmp_path / "mre.py"
    source.write_text(dedent('''
        class Thing:
            """A thing.

            Attributes:
                name (str): The documented attribute.
            """
            @property
            def name(self) -> str:
                """The name."""
            @name.setter
            def name(self, value):
                """Set the name."""
            @staticmethod
            def sm(x: int) -> int:
                """Static."""
            @classmethod
            def cm(cls) -> "Thing":
                """Class method."""
            def ordinary(self):
                """Instance method."""
    '''))
    output = tmp_path / f"mre.{renderer.file_extension}"
    assert generate_mdx(parse_module_fast("mre", source), output, renderer=renderer) is True
    content = output.read_text()
    assert content.count("#### `name`") == 1
    assert content.index("**Properties:**") < content.index("**Methods:**")
    assert "**Attributes:**" in content and "The documented attribute." in content
    assert "```python\nname: str\n```" in content
    assert "*Read/write.*" in content
    assert "The name." in content
    assert "**Setter:**" in content and "Set the name." in content
    assert "name(self" not in content
    assert "#### `sm`\n\n*Static method.*\n\n```python\nsm(x: int) -> int\n```" in content
    assert "#### `cm`\n\n*Class method.*\n\n```python\ncm() -> 'Thing'\n```" in content
    assert "#### `ordinary`\n\n```python\nordinary(self)\n```" in content


@pytest.mark.parametrize("setter,deleter,label", [
    (False, False, "*Read-only.*"),
    (True, False, "*Read/write.*"),
    (False, True, "*Read-only; deletable.*"),
    (True, True, "*Read/write; deletable.*"),
])
def test_property_output_variants(tmp_path, setter, deleter, label):
    prop = {
        "name": "name", "annotation": None, "docstring": "Get name.",
        "has_setter": setter, "has_deleter": deleter,
        "setter_docstring": "Set name." if setter else "",
        "deleter_docstring": "Delete name." if deleter else "",
    }
    module = {"name": "mre", "docstring": "", "functions": [], "classes": [
        {"name": "Thing", "docstring": "", "properties": [prop], "methods": []},
    ]}
    output = tmp_path / "mre.mdx"
    generate_mdx(module, output)
    content = output.read_text()
    assert "**Properties:**" in content
    assert "**Methods:**" not in content
    assert "```python\nname\n```" in content
    assert label in content
    assert "Get name." in content
    assert ("**Setter:**" in content) is setter
    assert ("**Deleter:**" in content) is deleter
    assert ("Set name." in content) is setter
    assert ("Delete name." in content) is deleter


@pytest.mark.parametrize("renderer,escaped", [
    (MDXRenderer(), "&lt;value&gt;"), (MarkdownRenderer(), "<value>"),
], ids=["mdx", "md"])
def test_property_source_links_and_escaping(tmp_path, renderer, escaped):
    src = tmp_path / "src" / "sample"
    src.mkdir(parents=True)
    source = src / "child.py"
    source.write_text("")
    base_source = src / "base.py"
    base_source.write_text("")
    module = {"name": "sample.child", "docstring": "", "functions": [], "source_file": str(source), "classes": [
        {"name": "Child", "docstring": "", "methods": [], "properties": [
            {"name": "local", "annotation": "list[str]", "line": 5,
             "docstring": "Getter <value> and `{name}`.", "has_setter": True, "has_deleter": True,
             "setter_docstring": "Set <value>.\n\nArgs:\n    value (str): New `{name}`.",
             "deleter_docstring": "Delete <value>."},
            {"name": "inherited", "annotation": "str", "line": 9, "docstring": "Base property.",
             "has_setter": False, "has_deleter": False, "is_inherited": True,
             "source_file": str(base_source)},
        ]},
    ]}
    output = tmp_path / f"result.{renderer.file_extension}"
    generate_mdx(module, output, renderer=renderer, repo_url="https://github.com/test/repo", root_module="sample")
    content = output.read_text()
    assert "https://github.com/test/repo/blob/main/src/sample/child.py#L5" in content
    assert "https://github.com/test/repo/blob/main/src/sample/base.py#L9" in content
    assert f"Getter {escaped} and `{{name}}`." in content
    assert f"Set {escaped}." in content
    assert f"Delete {escaped}." in content
    assert "**Args:**" in content
    assert "- `value`: New `{name}`." in content
    assert "```python\nlocal: list[str]\n```" in content


@pytest.mark.parametrize("properties", [None, []])
def test_empty_property_section_omitted(tmp_path, properties):
    cls = {"name": "Thing", "docstring": "", "methods": []}
    if properties is not None:
        cls["properties"] = properties
    module = {"name": "mre", "docstring": "", "functions": [], "classes": [cls]}
    output = tmp_path / "mre.mdx"
    generate_mdx(module, output)
    assert "**Properties:**" not in output.read_text()


def test_is_module_empty_detects_empty_content(tmp_path):
    """Test that empty module detection works."""
    mdx_file = tmp_path / "test.mdx"
    mdx_file.write_text("""
---
title: test
---

# `test.module`

*This module is empty or contains only private/internal implementations.*
""")
    
    assert is_module_empty(mdx_file) is True


def test_is_module_empty_detects_non_empty(tmp_path):
    """Test that non-empty modules are detected correctly."""
    mdx_file = tmp_path / "test.mdx"
    mdx_file.write_text("""
---
title: test
---

# `test.module`

This module has content.

## Functions

### `example`
""")
    
    assert is_module_empty(mdx_file) is False


def test_generate_mdx_empty_module_skipped_by_default(tmp_path):
    """Empty modules are not written to disk by default."""
    module_info = {
        "name": "test.empty",
        "docstring": "",
        "functions": [],
        "classes": [],
        "source_file": "/path/to/file.py"
    }

    output_file = tmp_path / "test-empty.mdx"
    wrote = generate_mdx(module_info, output_file)

    assert wrote is False
    assert not output_file.exists()


def test_generate_mdx_empty_module_removes_existing_stub(tmp_path):
    """A stub left by a previous run is removed when the module is empty."""
    module_info = {
        "name": "test.empty",
        "docstring": "",
        "functions": [],
        "classes": [],
        "source_file": "/path/to/file.py"
    }

    output_file = tmp_path / "test-empty.mdx"
    output_file.write_text(
        "*This module is empty or contains only private/internal implementations.*"
    )

    wrote = generate_mdx(module_info, output_file)

    assert wrote is False
    assert not output_file.exists()


def test_generate_mdx_empty_module_opt_out(tmp_path):
    """With skip_empty=False the placeholder page is still written."""
    module_info = {
        "name": "test.empty",
        "docstring": "",
        "functions": [],
        "classes": [],
        "source_file": "/path/to/file.py"
    }

    output_file = tmp_path / "test-empty.mdx"
    wrote = generate_mdx(module_info, output_file, skip_empty=False)

    assert wrote is True
    content = output_file.read_text()
    assert "title: empty" in content
    assert "*This module is empty or contains only private/internal implementations.*" in content


def test_generate_mdx_with_content(tmp_path):
    """Test generating MDX for a module with content."""
    module_info = {
        "name": "test.example",
        "docstring": "This is a test module.",
        "functions": [
            {
                "name": "test_function",
                "signature": "test_function(x: int) -> str",
                "docstring": "A test function.",
                "line": 10
            }
        ],
        "classes": [
            {
                "name": "TestClass",
                "docstring": "A test class.",
                "methods": [
                    {
                        "name": "test_method",
                        "signature": "test_method(self)",
                        "docstring": "A test method.",
                        "line": 20
                    }
                ],
                "line": 15
            }
        ],
        "source_file": "/path/to/file.py"
    }
    
    output_file = tmp_path / "test-example.mdx"
    generate_mdx(module_info, output_file)
    
    content = output_file.read_text()
    
    # Check frontmatter
    assert "title: example" in content
    assert "sidebarTitle: example" in content
    
    # Check module header
    assert "# `test.example`" in content
    assert "This is a test module." in content
    
    # Check functions section
    assert "## Functions" in content
    assert "### `test_function`" in content
    assert "test_function(x: int) -> str" in content
    assert "A test function." in content
    
    # Check classes section
    assert "## Classes" in content
    assert "### `TestClass`" in content
    assert "A test class." in content
    assert "#### `test_method`" in content
    assert "test_method(self)" in content

MIXED_MODULE_INFO = {
    "name": "pkg.mixed",
    "docstring": "Module docstring.",
    "functions": [
        {
            "name": "helper_one",
            "signature": "helper_one(x: int) -> str",
            "docstring": "First helper.",
            "line": 5,
        },
        {
            "name": "helper_two",
            "signature": "helper_two() -> None",
            "docstring": "",
            "line": 9,
        },
    ],
    "classes": [
        {
            "name": "Client",
            "docstring": "A client.",
            "line": 12,
            "methods": [
                {
                    "name": "connect",
                    "signature": "connect(self) -> None",
                    "docstring": "Open a connection.",
                    "line": 15,
                }
            ],
        }
    ],
    "source_file": "/path/to/pkg/mixed.py",
}

# Output of mdxify v0.2.45 for MIXED_MODULE_INFO; the default order must not change.
MIXED_MODULE_EXPECTED = (
    "---\ntitle: mixed\nsidebarTitle: mixed\n---\n\n# `pkg.mixed`\n\n\nModule docstring.\n\n"
    "## Functions\n\n### `helper_one`\n\n```python\nhelper_one(x: int) -> str\n```\n\n\n"
    "First helper.\n\n\n### `helper_two`\n\n```python\nhelper_two() -> None\n```\n\n"
    "## Classes\n\n### `Client`\n\n\nA client.\n\n\n**Methods:**\n\n#### `connect`\n\n"
    "```python\nconnect(self) -> None\n```\n\nOpen a connection.\n\n"
)


def test_generate_mdx_default_output_unchanged(tmp_path):
    """The default section order produces the same page as before the option existed."""
    output_file = tmp_path / "pkg-mixed.mdx"
    generate_mdx(MIXED_MODULE_INFO, output_file)

    assert output_file.read_text() == MIXED_MODULE_EXPECTED


def _section(content: str, heading: str) -> str:
    """Return the text of one H2 section, from its heading to the next H2 or the end."""
    start = content.index(heading)
    end = content.find("\n## ", start + len(heading))
    return content[start:] if end == -1 else content[start:end + 1]


def test_generate_mdx_explicit_functions_first_matches_default(tmp_path):
    """section_order="functions-first" is the same as the default."""
    output_file = tmp_path / "pkg-mixed.mdx"
    generate_mdx(MIXED_MODULE_INFO, output_file, section_order="functions-first")

    assert output_file.read_text() == MIXED_MODULE_EXPECTED


def test_generate_mdx_classes_first(tmp_path):
    """section_order="classes-first" moves Classes above Functions without changing either."""
    output_file = tmp_path / "pkg-mixed.mdx"
    generate_mdx(MIXED_MODULE_INFO, output_file, section_order="classes-first")
    content = output_file.read_text()

    assert content.index("## Classes") < content.index("## Functions")
    assert content.index("Module docstring.") < content.index("## Classes")
    for heading in ("## Functions", "## Classes"):
        assert _section(content, heading).rstrip("\n") == _section(
            MIXED_MODULE_EXPECTED, heading
        ).rstrip("\n")


@pytest.mark.parametrize("missing", ["functions", "classes"])
def test_generate_mdx_single_section_unaffected_by_order(tmp_path, missing):
    """A page with only one of the two sections is identical with either order."""
    module_info = {**MIXED_MODULE_INFO, missing: []}
    functions_first = tmp_path / "functions-first.mdx"
    classes_first = tmp_path / "classes-first.mdx"
    generate_mdx(module_info, functions_first, section_order="functions-first")
    generate_mdx(module_info, classes_first, section_order="classes-first")

    assert functions_first.read_text() == classes_first.read_text()


def test_generate_mdx_classes_first_markdown(tmp_path):
    """The section order also applies to Markdown output."""
    output_file = tmp_path / "pkg-mixed.md"
    generate_mdx(
        MIXED_MODULE_INFO,
        output_file,
        renderer=MarkdownRenderer(),
        section_order="classes-first",
    )
    content = output_file.read_text()

    assert content.index("## Classes") < content.index("## Functions")


def test_generate_mdx_rejects_unknown_section_order(tmp_path):
    """An unknown section_order raises ValueError and writes nothing."""
    output_file = tmp_path / "pkg-mixed.mdx"
    with pytest.raises(ValueError, match="functions-first, classes-first"):
        generate_mdx(MIXED_MODULE_INFO, output_file, section_order="foo")

    assert not output_file.exists()
