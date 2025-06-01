# Hoogle MCP Server

A Model Context Protocol (MCP) server for the Haskell API search engine
[Hoogle](https://hoogle.haskell.org/). This enables language models to search
for Haskell function definitions and type signatures using Hoogle commands.

## Requirements

- Python 3.8 or higher.
- [Hoogle](https://hoogle.haskell.org/) must be installed on the system.
  Refer to the [README](https://github.com/ndmitchell/hoogle) for installation
  instructions.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/toku-sa-n/hoogle-mcp-server
   cd hoogle-mcp-server
   ```

2. Install `hoogle-mcp-server` using [`pipx`](https://pipx.pypa.io/stable/):

   ```bash
   pipx install .
   ```

## MCP Configuration Example

Configuration example for use with Claude Desktop or MCP-compatible clients
(this configuration example is provided under the
[WTFPL license](https://www.wtfpl.net/about/)):

```json
{
  "mcpServers": {
    "hoogle": {
      "command": "hoogle-mcp-server",
      "env": {}
    }
  }
}
```

## Available tools

This MCP server provides the following tools:

### 1. `hoogle_search`

Search for Haskell functions and types using Hoogle.

**Parameters:**

- `query` (required): Search query (function name, type signature, keywords, etc.)
- `max_results` (optional): Maximum number of results (default: 10, max: 100)

**Example:**

```json
{
  "query": "map",
  "max_results": 5
}
```

### 2. `hoogle_info`

Get detailed information about a specific function or type using Hoogle's info search.

**Parameters:**

- `name` (required): Function name or type name to get detailed information
  for

**Example:**

```json
{
  "name": "map"
}
```

## License

This project is licensed under AGPL 3.0 or later. See the
[LICENSE](LICENSE) file for details.

## Contributing

Pull requests and issue reports are welcome.
