"""Tests for parser functionality."""

import sys
from textwrap import dedent
from unittest.mock import patch

from mdxify.parser import (
    ClassRegistry,
    extract_docstring,
    extract_function_signature,
    parse_module_fast,
    parse_modules_with_inheritance,
)


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
    
    