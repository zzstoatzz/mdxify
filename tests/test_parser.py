"""Tests for the parser module."""

import ast
from textwrap import dedent

from mdxify.parser import (
    extract_docstring,
    extract_function_signature,
    format_arg,
    parse_module_fast,
)


def test_extract_docstring_from_function():
    """Test extracting docstring from a function."""
    code = dedent('''
        def example():
            """This is a docstring."""
            pass
    ''')
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert extract_docstring(func_node) == "This is a docstring."


def test_extract_docstring_from_async_function():
    """Test extracting docstring from an async function."""
    code = dedent('''
        async def example():
            """This is a docstring."""
            pass
    ''')
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert extract_docstring(func_node) == "This is a docstring."


def test_extract_docstring_from_class():
    """Test extracting docstring from a class."""
    code = dedent('''
        class Example:
            """This is a class docstring."""
            pass
    ''')
    tree = ast.parse(code)
    class_node = tree.body[0]
    assert extract_docstring(class_node) == "This is a class docstring."


def test_extract_docstring_fixes_raises():
    """Test that Raises without colon is fixed."""
    code = dedent('''
        def example():
            """
            This function does something.
            
            Raises
                ValueError: If something is wrong.
            """
            pass
    ''')
    tree = ast.parse(code)
    func_node = tree.body[0]
    docstring = extract_docstring(func_node)
    assert "Raises:" in docstring
    assert "Raises\n" not in docstring


def test_format_arg_simple():
    """Test formatting a simple argument."""
    arg = ast.arg(arg="x", annotation=None)
    assert format_arg(arg) == "x"


def test_format_arg_with_annotation():
    """Test formatting an argument with type annotation."""
    arg = ast.arg(arg="x", annotation=ast.Name(id="int"))
    assert format_arg(arg) == "x: int"


def test_extract_function_signature_simple():
    """Test extracting a simple function signature."""
    code = "def foo(x, y): pass"
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)
    assert extract_function_signature(func_node) == "foo(x, y)"


def test_extract_async_function_signature_simple():
    """Test extracting a simple async function signature."""
    code = "async def foo(x, y): pass"
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.AsyncFunctionDef)
    assert extract_function_signature(func_node) == "foo(x, y)"


def test_extract_function_signature_with_types_and_defaults():
    """Test extracting function signature with type annotations and defaults."""
    code = "def foo(x: int, y: str = 'hello') -> bool: pass"
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef)
    assert extract_function_signature(func_node) == "foo(x: int, y: str = 'hello') -> bool"


def test_extract_async_function_signature_with_types_and_defaults():
    """Test extracting async function signature with type annotations and defaults."""
    code = "async def foo(x: int, y: str = 'hello') -> bool: pass"
    tree = ast.parse(code)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.AsyncFunctionDef)
    assert extract_function_signature(func_node) == "foo(x: int, y: str = 'hello') -> bool"


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

def test_parse_module_fast_includes_private_with_include_internal(tmp_path):
    """Test that private functions and classes are included when include_internal is True."""
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

    result = parse_module_fast("test_module", module_file, include_internal=True)
    
    assert result["name"] == "test_module"
    assert result["docstring"] == "Module docstring."
    assert len(result["functions"]) == 4
    assert result["functions"][0]["name"] == "public_function"
    assert result["functions"][1]["name"] == "_private_function"
    assert result["functions"][2]["name"] == "async_public_function"
    assert result["functions"][3]["name"] == "_async_private_function"
    assert len(result["classes"]) == 2
    assert result["classes"][0]["name"] == "PublicClass"
    assert len(result["classes"][0]["methods"]) == 4
    assert result["classes"][0]["methods"][0]["name"] == "public_method"
    assert result["classes"][0]["methods"][1]["name"] == "_private_method"
    assert result["classes"][0]["methods"][2]["name"] == "async_public_method"
    assert result["classes"][0]["methods"][3]["name"] == "_async_private_method"
    assert result["classes"][1]["name"] == "_PrivateClass"
    assert len(result["classes"][1]["methods"]) == 0
    