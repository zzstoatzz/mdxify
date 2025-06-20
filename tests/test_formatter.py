"""Tests for the formatter module."""


from mdxify.formatter import escape_mdx_content, format_docstring_with_griffe


def test_escape_mdx_content_preserves_code_blocks():
    """Test that code blocks are not escaped."""
    content = """
    Here is a dict[str, Any] type annotation.
    
    ```python
    def example(data: dict[str, Any]) -> list[int]:
        return [1, 2, 3]
    ```
    
    More text with list[str] type.
    """
    
    result = escape_mdx_content(content)
    
    # Type annotations outside code blocks should be escaped
    assert "dict\\[str, Any]" in result
    assert "list\\[str]" in result
    
    # But not inside code blocks
    assert "def example(data: dict[str, Any]) -> list[int]:" in result


def test_escape_mdx_content_handles_angle_brackets():
    """Test that angle brackets are converted to HTML entities."""
    content = "This is a <Tag> that should be escaped."
    result = escape_mdx_content(content)
    assert "&lt;Tag&gt;" in result
    assert "<Tag>" not in result


def test_escape_mdx_content_handles_todo():
    """Test that TODO: is escaped."""
    content = "TODO: Fix this later"
    result = escape_mdx_content(content)
    assert "TODO\\:" in result


def test_format_docstring_with_griffe_simple():
    """Test formatting a simple docstring."""
    docstring = """
    This is a simple function.
    
    Args:
        x: The first parameter
        y: The second parameter
        
    Returns:
        The sum of x and y
    """
    
    # The actual formatting depends on griffe being installed
    # For now, just test that it doesn't crash
    result = format_docstring_with_griffe(docstring)
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_docstring_escapes_colons_in_args():
    """Test that colons in parameter descriptions are escaped."""
    docstring = '''
    OAuth client implementation.
    
    Args:
        mcp_url: Full URL to the MCP endpoint (e.g., "http://host/mcp/sse/")
        scopes: OAuth scopes to request: Can be a space-separated string
    
    Raises:
        ValueError: If the URL is invalid: missing protocol or host
    '''
    
    result = format_docstring_with_griffe(docstring)
    
    # Check that colons in descriptions are escaped
    assert '- `mcp_url`: Full URL to the MCP endpoint (e.g., "http\\://host/mcp/sse/")' in result
    assert "- `scopes`: OAuth scopes to request\\: Can be a space-separated string" in result
    assert "- `ValueError`: If the URL is invalid\\: missing protocol or host" in result