"""Local stdio MCP adapter. The host owns this process; the browser stays open."""
import base64

from mcp.server import MCPServer
from mcp.server.mcpserver.utilities.types import Image
from mcp_types import ToolAnnotations

import browser_api as browser
from version import VERSION

mcp = MCPServer('Edge Agent', version=VERSION, instructions=(
    'Control the user-authorized local Microsoft Edge browser. Read status and tabs first. '
    'If disconnected, call edge_start to start Edge and the local service. '
    'Respect explicit pauses. First-time extension permissions require the user. '
    'Use real tab IDs. Never replay a timed-out action without checking the page. '
    'Do not stop the browser or service when the task ends.'
))
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)


@mcp.tool(annotations=READ)
def edge_status() -> dict:
    """Read the local browser connection status without exposing pairing credentials."""
    return browser.status()


@mcp.tool(annotations=WRITE)
def edge_start() -> dict:
    """Start the local service and existing Edge installation for an authorized browser task."""
    return browser.start()


@mcp.tool(annotations=READ)
def edge_tabs() -> dict:
    """List actual tab IDs and page titles/URLs from the connected browser."""
    return browser.tabs()


@mcp.tool(annotations=READ)
def edge_snapshot(tab_id: int, max_length: int = 10000, include_values: bool = False, frame: str = '') -> dict:
    """Read the page and its interactive elements before choosing a target."""
    return browser.command(tab_id, 'snapshot', {'max_length': max_length, 'include_values': include_values, 'frame': frame})


@mcp.tool(annotations=WRITE)
def edge_click(tab_id: int, selector: str = '', text: str = '', ref: int | None = None, frame: str = '') -> dict:
    """Click an element using exactly one observed CSS selector or text match."""
    return browser.command(tab_id, 'click', browser.locate(selector=selector, text=text, ref=ref, frame=frame))


@mcp.tool(annotations=WRITE)
def edge_fill(tab_id: int, value: str, selector: str = '', label: str = '', ref: int | None = None, frame: str = '') -> dict:
    """Fill a field using exactly one observed CSS selector or label."""
    args = browser.locate(selector=selector, label=label, ref=ref, frame=frame)
    return browser.command(tab_id, 'fill', {**args, 'value': value})


@mcp.tool(annotations=WRITE)
def edge_select(tab_id: int, value: str, selector: str = '', label: str = '', ref: int | None = None, frame: str = '') -> dict:
    """Select an option using exactly one observed CSS selector or label."""
    args = browser.locate(selector=selector, label=label, ref=ref, frame=frame)
    return browser.command(tab_id, 'select', {**args, 'value': value})


@mcp.tool(annotations=WRITE)
def edge_navigate(tab_id: int, url: str) -> dict:
    """Navigate an existing tab to an authorized HTTP/HTTPS URL."""
    return browser.command(tab_id, 'navigate', {'url': url})


@mcp.tool(annotations=WRITE)
def edge_new_tab(url: str = 'about:blank') -> dict:
    """Open a tab and return its actual browser ID."""
    return browser.command(0, 'new_tab', {'url': url})


@mcp.tool(annotations=WRITE)
def edge_activate(tab_id: int) -> dict:
    """Activate a tab using an ID returned by edge_tabs."""
    return browser.command(tab_id, 'activate')


@mcp.tool(annotations=WRITE)
def edge_close_tab(tab_id: int) -> dict:
    """Close a specific tab only when the user's task calls for it."""
    return browser.command(tab_id, 'close_tab')


@mcp.tool(annotations=WRITE)
def edge_evaluate(tab_id: int, expression: str) -> dict:
    """Run JavaScript in an authorized webpage. Execution can change the page."""
    return {'value': browser.command(tab_id, 'eval', {'expression': expression})}


@mcp.tool(annotations=READ)
def edge_screenshot(tab_id: int) -> Image:
    """Return a PNG image of a connected tab directly to the agent."""
    result = browser.command(tab_id, 'screenshot')
    return Image(data=base64.b64decode(result['data'], validate=True), format='png')


@mcp.tool(annotations=READ)
def edge_doctor() -> dict:
    """Diagnose this installation without starting services or returning secrets/tab contents."""
    from diagnostics import diagnose
    return diagnose()


@mcp.tool(annotations=READ)
def edge_wait(tab_id: int, selector: str = '', text: str = '', ref: int | None = None,
              frame: str = '', state: str = 'visible', timeout: float = 30) -> dict:
    """Wait for visible/hidden/attached/detached/enabled or document ready. Never replays actions."""
    return browser.wait(tab_id, selector, text, ref, frame, state, timeout)


@mcp.tool(annotations=WRITE)
def edge_upload(tab_id: int, files: list[str], selector: str = '', ref: int | None = None, frame: str = '') -> dict:
    """Set a real file input to explicitly selected local files. Returns names/sizes, not file contents."""
    return browser.upload(tab_id, files, selector, ref, frame)


@mcp.tool(annotations=WRITE)
def edge_download(tab_id: int, directory: str, selector: str = '', ref: int | None = None,
                  frame: str = '', timeout: float = 60) -> dict:
    """Stream an observed HTTP/HTTPS file link through the current Edge frame to the specified directory. Keeps authentication in Edge; never executes the file."""
    return browser.download(tab_id, directory, selector, ref, frame, timeout)


@mcp.tool(annotations=READ)
def edge_download_status(tab_id: int, download_id: str) -> dict:
    """Read a transfer ID created by edge_download in this tab/local service, without listing unrelated downloads."""
    return browser.command(tab_id, 'download_status', {'download_id': download_id})


@mcp.tool(annotations=READ)
def edge_workflow(name: str) -> dict:
    """Read a reusable literature-search or reference-check workflow for the current agent to execute."""
    return browser.workflow(name)


if __name__ == '__main__':
    mcp.run(transport='stdio')
