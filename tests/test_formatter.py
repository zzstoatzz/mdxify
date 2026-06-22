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


def test_format_docstring_with_examples_section():
    """Test that Examples section is rendered as a bold header like Args/Returns."""
    docstring = '''
    Creates a deployment for this flow and starts a runner to monitor for scheduled work.

    Args:
        name: The name to give the created deployment. Defaults to the name of the flow.
        interval: An interval on which to execute the deployment. Accepts a number or a
            timedelta object to create a single schedule. If a number is given, it will be
            interpreted as seconds. Also accepts an iterable of numbers or timedelta to create
            multiple schedules.
        cron: A cron schedule string of when to execute runs of this deployment.
            Also accepts an iterable of cron schedule strings to create multiple schedules.
        rrule: An rrule schedule string of when to execute runs of this deployment.
            Also accepts an iterable of rrule schedule strings to create multiple schedules.
        triggers: A list of triggers that will kick off runs of this deployment.
        paused: Whether or not to set this deployment as paused.
        schedule: A schedule object defining when to execute runs of this deployment.
            Used to provide additional scheduling options like `timezone` or `parameters`.
        schedules: A list of schedule objects defining when to execute runs of this deployment.
            Used to define multiple schedules or additional scheduling options like `timezone`.
        global_limit: The maximum number of concurrent runs allowed across all served flow instances associated with the same deployment.
        parameters: A dictionary of default parameter values to pass to runs of this deployment.
        description: A description for the created deployment. Defaults to the flow's
            description if not provided.
        tags: A list of tags to associate with the created deployment for organizational
            purposes.
        version: A version for the created deployment. Defaults to the flow's version.
        enforce_parameter_schema: Whether or not the Prefect API should enforce the
            parameter schema for the created deployment.
        pause_on_shutdown: If True, provided schedule will be paused when the serve function is stopped.
            If False, the schedules will continue running.
        print_starting_message: Whether or not to print the starting message when flow is served.
        limit: The maximum number of runs that can be executed concurrently by the created runner; only applies to this served flow. To apply a limit across multiple served flows, use `global_limit`.
        webserver: Whether or not to start a monitoring webserver for this flow.
        entrypoint_type: Type of entrypoint to use for the deployment. When using a module path
            entrypoint, ensure that the module will be importable in the execution environment.

    Examples:
        Serve a flow:

        ```python
        from prefect import flow

        @flow
        def my_flow(name):
            print(f"hello {name}")

        if __name__ == "__main__":
            my_flow.serve("example-deployment")
        ```

        Serve a flow and run it every hour:

        ```python
        from prefect import flow

        @flow
        def my_flow(name):
            print(f"hello {name}")

        if __name__ == "__main__":
            my_flow.serve("example-deployment", interval=3600)
        ```
    '''
    
    result = format_docstring_with_griffe(docstring)
    
    # Check that Examples is rendered as a bold header
    assert "**Examples:**" in result
    # Check that other sections are also bold
    assert "**Args:**" in result


def test_format_docstring_with_attributes_section():
    """Test that Attributes section in class docstrings is rendered correctly.

    Regression test for issue #32.
    """
    docstring = '''Schema for a column in a table.

    Attributes:
        name (str): The name of the column.
        type (str): The data type of the column, represented as a string.
    '''

    result = format_docstring_with_griffe(docstring)

    # Check that Attributes is rendered as a bold header
    assert "**Attributes:**" in result
    # Check that attribute names are properly formatted
    assert "- `name`:" in result
    assert "- `type`:" in result
    # Check that descriptions are present
    assert "The name of the column" in result
    assert "The data type of the column" in result


def test_format_docstring_with_attributes_and_methods():
    """Test class docstring with both Attributes and other sections."""
    docstring = '''Configuration for database connections.

    Attributes:
        host (str): The database host address.
        port (int): The port number for the connection.

    Examples:
        >>> config = DatabaseConfig("localhost", 5432)
        >>> print(config.host)
        localhost
    '''

    result = format_docstring_with_griffe(docstring)

    # Check that both sections are rendered
    assert "**Attributes:**" in result
    assert "**Examples:**" in result
    # Check ordering - Attributes should come before Examples
    assert result.index("**Attributes:**") < result.index("**Examples:**")


def test_format_docstring_with_numpy_style():
    """Test formatting NumPy-style docstrings.

    Addresses issue #31 - docstring style should be configurable.
    """
    docstring = '''Calculate the mean of values.

    Parameters
    ----------
    values : list
        A list of numeric values.

    Returns
    -------
    float
        The arithmetic mean.

    Attributes
    ----------
    result : float
        The computed result.
    '''

    result = format_docstring_with_griffe(docstring, style="numpy")

    # Check that Args is rendered (Parameters -> Args)
    assert "**Args:**" in result
    assert "- `values`:" in result
    # Check Returns
    assert "**Returns:**" in result
    # Check Attributes
    assert "**Attributes:**" in result
    assert "- `result`:" in result


def test_format_docstring_with_sphinx_style():
    """Test formatting Sphinx-style docstrings."""
    docstring = '''Process the given data.

    :param data: The input data.
    :type data: list
    :returns: Processed data.
    :rtype: dict
    '''

    result = format_docstring_with_griffe(docstring, style="sphinx")

    # Check that Args is rendered
    assert "**Args:**" in result
    assert "- `data`:" in result
    # Check Returns
    assert "**Returns:**" in result


def test_format_docstring_style_default_is_google():
    """Test that Google style is the default."""
    docstring = '''A simple function.

    Args:
        x: First parameter.
    '''

    # Call without style parameter - should use google
    result = format_docstring_with_griffe(docstring)

    assert "**Args:**" in result
    assert "- `x`:" in result