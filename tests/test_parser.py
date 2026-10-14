"""Tests for parser functionality."""

import ast
import sys
from textwrap import dedent
from unittest.mock import patch

import pytest

from mdxify.parser import (
    ClassRegistry,
    extract_docstring,
    extract_function_signature,
    extract_methods_from_class,
    parse_module_fast,
    parse_modules_with_inheritance,
)


def test_decorator_aware_class_members(tmp_path):
    module_file = tmp_path / "mre.py"
    module_file.write_text(dedent('''\
        class Thing:
            """A thing."""

            @property
            def name(self) -> str:
                """The name."""
                return "n"

            @name.setter
            def name(self, value: str) -> None:
                """Set the name."""

            @staticmethod
            def sm(x: int) -> int:
                """Static."""
                return x

            @classmethod
            def cm(cls) -> "Thing":
                """Class method."""
                return cls()
    '''))
    cls = parse_module_fast("mre", module_file)["classes"][0]
    assert [m["name"] for m in cls["methods"]] == ["sm", "cm"]
    assert [m["kind"] for m in cls["methods"]] == ["static", "class"]
    assert cls["methods"][0]["signature"] == "sm(x: int) -> int"
    assert cls["methods"][1]["signature"] == "cm() -> 'Thing'"
    assert cls["properties"] == [{
        "name": "name", "annotation": "str", "docstring": "The name.",
        "line": 5, "has_setter": True, "has_deleter": False,
        "setter_docstring": "Set the name.", "deleter_docstring": "",
        "is_inherited": False,
    }]
    node = ast.parse(module_file.read_text()).body[0]
    assert isinstance(node, ast.ClassDef)
    assert extract_methods_from_class(node) == cls["methods"]


@pytest.mark.parametrize("setter,deleter", [(False, False), (True, False), (False, True), (True, True)])
def test_property_accessor_variants(tmp_path, setter, deleter):
    source = 'class Thing:\n    @property\n    def name(self):\n        """Get name."""\n'
    if setter:
        source += '    @name.setter\n    def name(self, value: str):\n        """Set name."""\n'
    if deleter:
        source += '    @name.deleter\n    def name(self):\n        """Delete name."""\n'
    module_file = tmp_path / "members.py"
    module_file.write_text(source)
    cls = parse_module_fast("members", module_file)["classes"][0]
    assert cls["methods"] == []
    assert len(cls["properties"]) == 1
    prop = cls["properties"][0]
    assert prop["annotation"] is None
    assert prop["docstring"] == "Get name."
    assert prop["line"] == 3
    assert prop["has_setter"] is setter
    assert prop["has_deleter"] is deleter
    assert prop["setter_docstring"] == ("Set name." if setter else "")
    assert prop["deleter_docstring"] == ("Delete name." if deleter else "")


def test_property_getter_replacement_and_private_filter(tmp_path):
    module_file = tmp_path / "members.py"
    module_file.write_text(dedent('''\
        class Thing:
            @property
            def name(self) -> int:
                """Old getter."""
            @name.setter
            def name(self, value):
                """Setter."""
            @name.getter
            def name(self) -> str:
                """New getter."""
            @property
            def _secret(self):
                """Secret."""
            @_secret.setter
            def _secret(self, value):
                pass
    '''))
    for include_internal in (False, True):
        cls = parse_module_fast("members", module_file, include_internal)["classes"][0]
        assert cls["methods"] == []
        assert [p["name"] for p in cls["properties"]] == (["name", "_secret"] if include_internal else ["name"])
        prop = cls["properties"][0]
        assert (prop["annotation"], prop["docstring"], prop["line"]) == ("str", "New getter.", 9)
        assert prop["has_setter"] is True
        assert prop["setter_docstring"] == "Setter."


def test_decorator_classification(tmp_path):
    module_file = tmp_path / "members.py"
    module_file.write_text(dedent('''
        class Thing:
            @builtins.property
            @abstractmethod
            def name(self) -> str:
                pass
            @name.setter
            def name(self, value):
                pass
            @builtins.staticmethod
            @abstractmethod
            async def sm(cls: int) -> int:
                pass
            @abstractmethod
            @builtins.classmethod
            async def cm(receiver, value: int) -> int:
                pass
            def normal(self):
                pass
            @other.setter
            def unrelated(self, value):
                pass
            @other.property
            def custom(self):
                pass
    '''))
    cls = parse_module_fast("members", module_file)["classes"][0]
    assert [p["name"] for p in cls["properties"]] == ["name"]
    assert cls["properties"][0]["has_setter"] is True
    assert [(m["name"], m["kind"]) for m in cls["methods"]] == [
        ("sm", "static"), ("cm", "class"), ("normal", "instance"),
        ("unrelated", "instance"), ("custom", "instance"),
    ]
    assert cls["methods"][0]["signature"] == "sm(cls: int) -> int"
    assert cls["methods"][1]["signature"] == "cm(value: int) -> int"
    assert cls["methods"][2]["signature"] == "normal(self)"


@pytest.mark.parametrize("arguments,expected", [
    ("receiver, /, x: int = 1, *, flag: bool = False", "build(x: int = 1, *, flag: bool = False) -> str"),
    ("receiver, x: int, /, y=2", "build(x: int, /, y = 2) -> str"),
    ("receiver=None, x=1", "build(x = 1) -> str"),
    ("receiver, *args: int, flag=True, **kwargs: str", "build(*args: int, flag = True, **kwargs: str) -> str"),
    ("receiver, **kwargs", "build(**kwargs) -> str"),
    ("receiver", "build() -> str"),
    ("*, flag", "build(*, flag) -> str"),
])
def test_classmethod_signature_receiver(arguments, expected):
    node = ast.parse(f"def build({arguments}) -> str:\n    pass").body[0]
    assert isinstance(node, ast.FunctionDef)
    before = ast.dump(node)
    assert extract_function_signature(node, skip_first_arg=True) == expected
    assert ast.dump(node) == before


def test_function_signature_argument_groups():
    node = ast.parse("def build(x: int = 1, /, *, flag: bool, limit=2, **kwargs) -> str:\n    pass").body[0]
    assert isinstance(node, ast.FunctionDef)
    assert extract_function_signature(node) == "build(x: int = 1, /, *, flag: bool, limit = 2, **kwargs) -> str"


def test_inherited_decorated_members_from_private_module(tmp_path, monkeypatch):
    base_file = tmp_path / "_internal.py"
    base_file.write_text(dedent('''\
        class _Base:
            @property
            def name(self) -> str:
                """Base name."""
            @name.setter
            def name(self, value):
                """Set base name."""
            @property
            def _secret(self):
                pass
            @staticmethod
            def sm(x: int) -> int:
                return x
            @classmethod
            def cm(cls) -> str:
                return "base"
    '''))
    child_file = tmp_path / "public.py"
    child_file.write_text("class Child(_Base):\n    pass\n")
    files = {"_internal": base_file, "public": child_file}
    monkeypatch.setattr("mdxify.discovery.find_all_modules", lambda root: list(files))
    monkeypatch.setattr("mdxify.discovery.get_module_source_file", files.get)

    for include_internal in (False, True):
        child = parse_modules_with_inheritance(["public"], include_internal)["public"]["classes"][0]
        assert [m["name"] for m in child["methods"]] == ["cm", "sm"]
        assert [(m["kind"], m["signature"]) for m in child["methods"]] == [
            ("class", "cm() -> str"), ("static", "sm(x: int) -> int"),
        ]
        assert [p["name"] for p in child["properties"]] == (["_secret", "name"] if include_internal else ["name"])
        prop = next(p for p in child["properties"] if p["name"] == "name")
        assert (prop["annotation"], prop["docstring"], prop["line"]) == ("str", "Base name.", 3)
        assert prop["has_setter"] is True
        assert prop["setter_docstring"] == "Set base name."
        assert prop["is_inherited"] is True
        assert prop["inherited_from"] == "_Base"
        assert prop["source_file"] == str(base_file)


@pytest.mark.parametrize("base_member,local_member,expected_kind", [
    ("@property\ndef value(self) -> str:\n    pass", "@property\ndef value(self) -> int:\n    pass", "property"),
    ("@property\ndef value(self) -> str:\n    pass", "def value(self):\n    pass", "method"),
    ("def value(self):\n    pass", "@property\ndef value(self) -> int:\n    pass", "property"),
    ("def value(self):\n    pass", "def value(self):\n    pass", "method"),
    ("@property\ndef value(self) -> str:\n    pass", "value = None", None),
    ("@property\ndef value(self) -> str:\n    pass", "value: int = 1", None),
])
def test_local_member_shadows_inherited_member(tmp_path, base_member, local_member, expected_kind):
    from textwrap import indent

    module_file = tmp_path / "members.py"
    module_file.write_text("class Base:\n" + indent(base_member, "    ") + "\nclass Child(Base):\n" + indent(local_member, "    "))
    local = parse_module_fast("members", module_file)
    registry = ClassRegistry()
    for cls in local["classes"]:
        registry.add_class("members", cls["name"], cls, str(module_file))
    child = parse_module_fast("members", module_file, class_registry=registry)["classes"][1]
    members = child["properties"] + child["methods"]
    assert len(members) == (0 if expected_kind is None else 1)
    assert all(m["is_inherited"] is False for m in members)
    if expected_kind == "property":
        assert child["methods"] == []
        assert child["properties"][0]["annotation"] == "int"
    elif expected_kind == "method":
        assert child["properties"] == []
        assert child["methods"][0]["signature"] == "value(self)"


@pytest.mark.parametrize("first_member,second_member,expected_kind", [
    ("@property\ndef value(self) -> int:\n    pass", "@property\ndef value(self) -> str:\n    pass", "property"),
    ("@property\ndef value(self) -> int:\n    pass", "def value(self):\n    pass", "property"),
    ("def value(self):\n    pass", "@property\ndef value(self) -> str:\n    pass", "method"),
    ("value = None", "@property\ndef value(self) -> str:\n    pass", None),
])
def test_inherited_members_first_base_wins(tmp_path, first_member, second_member, expected_kind):
    from textwrap import indent

    module_file = tmp_path / "members.py"
    module_file.write_text("class First:\n" + indent(first_member, "    ") + "\nclass Second:\n" + indent(second_member, "    ") + "\nclass Child(First, Second):\n    pass")
    local = parse_module_fast("members", module_file)
    registry = ClassRegistry()
    for cls in local["classes"]:
        registry.add_class("members", cls["name"], cls, str(module_file))
    child = parse_module_fast("members", module_file, class_registry=registry)["classes"][2]
    if expected_kind is None:
        assert child["properties"] + child["methods"] == []
        return
    assert len(child["properties"] + child["methods"]) == 1
    member = (child["properties"] + child["methods"])[0]
    assert member["inherited_from"] == "First"
    assert member["source_file"] == str(module_file)
    if expected_kind == "property":
        assert child["methods"] == []
        assert member["annotation"] == "int"
    else:
        assert child["properties"] == []


def test_inherited_properties_legacy_registry_and_no_mutation(tmp_path):
    base_file = tmp_path / "base.py"
    base_file.write_text("class Base:\n    @property\n    def value(self) -> int:\n        pass")
    base = parse_module_fast("base", base_file)["classes"][0]
    registry = ClassRegistry()
    registry.add_class("base", "Base", base, str(base_file))
    registry.add_class("child", "Child", {"base_classes": ["Base"], "methods": []})
    inherited = registry.get_inherited_properties("child.Child")
    assert len(inherited) == 1
    assert inherited[0]["is_inherited"] is True
    assert base["properties"][0]["is_inherited"] is False
    assert "source_file" not in base["properties"][0]
    registry.add_class("base", "Legacy", {"methods": [{"name": "work", "signature": "work(self)"}], "base_classes": []})
    registry.add_class("child", "LegacyChild", {"base_classes": ["Legacy"], "methods": []})
    assert registry.get_inherited_properties("child.LegacyChild") == []
    assert registry.get_inherited_properties("missing") == []
    assert registry.get_inherited_methods("child.LegacyChild")[0]["name"] == "work"


@pytest.mark.parametrize("replacement,expected_methods", [
    ("def value(self):\n    pass", ["value"]),
    ("value = None", []),
    ("value: int = 1", []),
    ("class value:\n    pass", []),
])
def test_local_property_rebinding(tmp_path, replacement, expected_methods):
    from textwrap import indent

    module_file = tmp_path / "members.py"
    module_file.write_text("class Thing:\n    @property\n    def value(self) -> str:\n        pass\n" + indent(replacement, "    "))
    cls = parse_module_fast("members", module_file)["classes"][0]
    assert cls["properties"] == []
    assert [m["name"] for m in cls["methods"]] == expected_methods


def test_local_property_replaces_method(tmp_path):
    module_file = tmp_path / "members.py"
    module_file.write_text("class Thing:\n    def value(self):\n        pass\n    @property\n    def value(self) -> str:\n        pass")
    cls = parse_module_fast("members", module_file)["classes"][0]
    assert cls["methods"] == []
    assert [p["name"] for p in cls["properties"]] == ["value"]


def test_annotation_only_does_not_shadow_inherited_property(tmp_path):
    module_file = tmp_path / "members.py"
    module_file.write_text("class Base:\n    @property\n    def value(self) -> str:\n        pass\nclass Child(Base):\n    value: str")
    local = parse_module_fast("members", module_file)
    registry = ClassRegistry()
    for cls in local["classes"]:
        registry.add_class("members", cls["name"], cls)
    child = parse_module_fast("members", module_file, class_registry=registry)["classes"][1]
    assert [p["name"] for p in child["properties"]] == ["value"]
    assert child["properties"][0]["is_inherited"] is True


def test_extract_docstring():
    """Test docstring extraction."""
    import ast

    # Test function docstring
    func_code = 'def test():\n    """Test docstring."""\n    pass'
    func_ast = ast.parse(func_code).body[0]
    assert extract_docstring(func_ast) == "Test docstring."

    # Test async function docstring
    async_func_code = 'async def test():\n    """Test docstring."""\n    pass'
    async_func_ast = ast.parse(async_func_code).body[0]
    assert extract_docstring(async_func_ast) == "Test docstring."

    # Test class docstring
    class_code = 'class Test:\n    """Test class docstring."""\n    pass'
    class_ast = ast.parse(class_code).body[0]
    assert extract_docstring(class_ast) == "Test class docstring."

    # Test module docstring
    module_code = '"""Test module docstring."""\npass'
    module_ast = ast.parse(module_code)
    assert extract_docstring(module_ast) == "Test module docstring."

    # Test no docstring
    no_doc_code = "def test():\n    pass"
    no_doc_ast = ast.parse(no_doc_code).body[0]
    assert extract_docstring(no_doc_ast) == ""


def test_extract_function_signature():
    """Test function signature extraction."""
    import ast

    # Simple function
    func_code = "def test(x: int, y: str = 'default') -> bool:\n    pass"
    func_ast = ast.parse(func_code).body[0]
    assert isinstance(func_ast, ast.FunctionDef)
    assert extract_function_signature(func_ast) == "test(x: int, y: str = 'default') -> bool"

    # Function with *args and **kwargs
    func_code = "def test(x: int, *args, **kwargs) -> None:\n    pass"
    func_ast = ast.parse(func_code).body[0]
    assert isinstance(func_ast, ast.FunctionDef)
    assert extract_function_signature(func_ast) == "test(x: int, *args, **kwargs) -> None"

    # Function with types and defaults
    func_code = "def test(x: int = 1, y: str = 'default') -> bool:\n    pass"
    func_ast = ast.parse(func_code).body[0]
    assert isinstance(func_ast, ast.FunctionDef)
    assert extract_function_signature(func_ast) == "test(x: int = 1, y: str = 'default') -> bool"

    # Async function
    func_code = "async def test(x: int) -> str:\n    pass"
    func_ast = ast.parse(func_code).body[0]
    assert isinstance(func_ast, ast.AsyncFunctionDef)
    assert extract_function_signature(func_ast) == "test(x: int) -> str"


def test_parse_module_fast(tmp_path):
    """Test parsing a module file."""
    module_file = tmp_path / "test_module.py"
    module_file.write_text(dedent('''
        """Module docstring."""
        
        def public_function(x: int) -> int:
            """A public function."""
            return x * 2
            
        def _private_function():
            """A private function."""
            pass

        async def async_public_function(x: int) -> int:
            """An async public function."""
            return x * 2

        async def _async_private_function():
            """An async private function."""
            pass
            
        class PublicClass:
            """A public class."""
            
            def public_method(self):
                """A public method."""
                pass
                
            def _private_method(self):
                """A private method."""
                pass

            async def async_public_method(self):
                """An async public method."""
                pass

            async def _async_private_method(self):
                """An async private method."""
                pass
                                  
        class _PrivateClass:
            """A private class."""
            pass
    '''))
    
    result = parse_module_fast("test_module", module_file)
    
    assert result["name"] == "test_module"
    assert result["docstring"] == "Module docstring."
    assert len(result["functions"]) == 2
    assert result["functions"][0]["name"] == "public_function"
    assert result["functions"][1]["name"] == "async_public_function"
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "PublicClass"
    assert len(result["classes"][0]["methods"]) == 2
    assert result["classes"][0]["methods"][0]["name"] == "public_method"
    assert result["classes"][0]["methods"][1]["name"] == "async_public_method"


def test_parse_module_fast_with_inheritance(tmp_path):
    """Test parsing a module with inheritance support."""
    # Create parent module
    parent_file = tmp_path / "parent_module.py"
    parent_file.write_text(dedent('''
        """Parent module."""
        
        class BaseClass:
            """A base class with methods."""
            
            def base_method(self, x: int) -> int:
                """A method from the base class.
                
                Args:
                    x: Input value
                    
                Returns:
                    Doubled value
                """
                return x * 2
                
            def another_method(self, text: str) -> str:
                """Another method from base class.
                
                Args:
                    text: Input text
                    
                Returns:
                    Uppercase text
                """
                return text.upper()
    '''))
    
    # Create child module
    child_file = tmp_path / "child_module.py"
    child_file.write_text(dedent('''
        """Child module."""
        
        from .parent_module import BaseClass
        
        class ChildClass(BaseClass):
            """A child class that inherits from BaseClass."""
            
            def child_method(self, value: str) -> str:
                """A method specific to the child class.
                
                Args:
                    value: Input value
                    
                Returns:
                    Processed value
                """
                return f"Child: {value}"
    '''))
    
    # Test inheritance parsing
    modules_to_process = ["parent_module", "child_module"]
    
    # Mock the module discovery to use our test files
    import sys
    sys.path.insert(0, str(tmp_path))
    
    try:
        # Mock get_module_source_file to return our test files
        from unittest.mock import patch
        
        def mock_get_module_source_file(module_name):
            if module_name == "parent_module":
                return parent_file
            elif module_name == "child_module":
                return child_file
            return None
        
        with patch('mdxify.discovery.get_module_source_file', side_effect=mock_get_module_source_file):
            results = parse_modules_with_inheritance(modules_to_process)
            
            # Check that we got results for both modules
            assert "parent_module" in results
            assert "child_module" in results
            
            # Check parent module
            parent_result = results["parent_module"]
            assert len(parent_result["classes"]) == 1
            assert parent_result["classes"][0]["name"] == "BaseClass"
            assert len(parent_result["classes"][0]["methods"]) == 2
            
            # Check child module
            child_result = results["child_module"]
            assert len(child_result["classes"]) == 1
            assert child_result["classes"][0]["name"] == "ChildClass"
            
            # Child should have its own method plus inherited methods
            child_methods = child_result["classes"][0]["methods"]
            assert len(child_methods) == 3  # 1 own + 2 inherited
            
            # Find the inherited methods
            inherited_methods = [m for m in child_methods if m.get("is_inherited")]
            assert len(inherited_methods) == 2
            
            # Check that inherited methods have the right metadata
            for method in inherited_methods:
                assert method["is_inherited"] is True
                assert method["inherited_from"] == "BaseClass"
                assert method["name"] in ["base_method", "another_method"]
                
    finally:
        sys.path.remove(str(tmp_path))


def test_class_registry():
    """Test the ClassRegistry functionality."""
    registry = ClassRegistry()
    
    # Add a class
    class_info = {
        "name": "TestClass",
        "methods": [{"name": "test_method", "signature": "test_method()"}],
        "base_classes": ["BaseClass"]
    }
    
    registry.add_class("test_module", "TestClass", class_info)
    
    # Check that it was added
    assert registry.get_class("test_module.TestClass") == class_info
    assert "test_module" in registry.module_classes
    assert "TestClass" in registry.module_classes["test_module"]
    
    # Test finding class in modules
    found = registry.find_class_in_modules("TestClass", ["test_module"])
    assert found == "test_module.TestClass"
    
    # Test with non-existent class
    found = registry.find_class_in_modules("NonExistent", ["test_module"])
    assert found is None


def test_inheritance_with_complex_base_classes(tmp_path):
    """Test inheritance with complex base class references."""
    # Create a module with complex inheritance
    module_file = tmp_path / "complex_inheritance.py"
    module_file.write_text(dedent('''
        """Module with complex inheritance."""
        
        from typing import List, Optional
        
        class BaseClass:
            """Base class."""
            
            def base_method(self) -> str:
                """Base method."""
                return "base"
        
        class IntermediateClass(BaseClass):
            """Intermediate class."""
            
            def intermediate_method(self) -> str:
                """Intermediate method."""
                return "intermediate"
        
        class FinalClass(IntermediateClass):
            """Final class with multiple inheritance levels."""
            
            def final_method(self) -> str:
                """Final method."""
                return "final"
    '''))
    
    # Test parsing
    result = parse_module_fast("complex_inheritance", module_file)
    
    assert len(result["classes"]) == 3
    
    # Check that base classes are extracted correctly
    base_class = next(c for c in result["classes"] if c["name"] == "BaseClass")
    assert base_class["base_classes"] == []
    
    intermediate_class = next(c for c in result["classes"] if c["name"] == "IntermediateClass")
    assert intermediate_class["base_classes"] == ["BaseClass"]
    
    final_class = next(c for c in result["classes"] if c["name"] == "FinalClass")
    assert final_class["base_classes"] == ["IntermediateClass"]
    

def test_inheritance_from_private_module(tmp_path):
    """Test that public methods from parent classes in private modules are included in child class documentation."""
    # Create a private parent module
    private_file = tmp_path / "_internal.py"
    private_file.write_text(dedent('''
        """Private internal module."""
        
        class _Base:
            """A private base class with a public method."""
            def public_base_method(self, x: int) -> int:
                """A public method from the private base class."""
                return x * 2
            def _private_base_method(self):
                """A private method from the private base class."""
                pass
    '''))
    # Create a public child module
    public_file = tmp_path / "public_mod.py"
    public_file.write_text(dedent('''
        """Public module."""
        from _internal import _Base
        class PublicChild(_Base):
            """A public child class inheriting from a private base class."""
            def child_method(self):
                """A method specific to the child class."""
                pass
    '''))
    # Patch get_module_source_file and find_all_modules
    
    sys.path.insert(0, str(tmp_path))
    
    def mock_get_module_source_file(module_name):
        if module_name == "_internal":
            return private_file
        elif module_name == "public_mod":
            return public_file
        return None
    
    def mock_find_all_modules(root_module):
        return ["_internal", "public_mod"]
    try:
        with patch('mdxify.discovery.get_module_source_file', side_effect=mock_get_module_source_file), \
             patch('mdxify.discovery.find_all_modules', side_effect=mock_find_all_modules):
            results = parse_modules_with_inheritance(["public_mod"])
            child = results["public_mod"]["classes"][0]
            method_names = {m["name"] for m in child["methods"]}
            # Should include both the child method and the inherited public method
            assert "child_method" in method_names
            assert "public_base_method" in method_names
            # Should not include the private method from the base
            assert "_private_base_method" not in method_names
            # The inherited method should be marked as inherited
            inherited = [m for m in child["methods"] if m["name"] == "public_base_method"]
            assert inherited and inherited[0]["is_inherited"] is True
    finally:
        sys.path.remove(str(tmp_path))
