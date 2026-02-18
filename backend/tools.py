generate_cad_prototype_tool = {
    "name": "generate_cad_prototype",
    "description": "Generates a 3D wireframe prototype based on a user's description. Use this when the user asks to 'visualize', 'prototype', 'create a wireframe', or 'design' something in 3D.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The user's description of the object to prototype."
            }
        },
        "required": ["prompt"]
    }
}

write_file_tool = {
    "name": "write_file",
    "description": "Writes content to a file at the specified path. Overwrites if exists.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to write to."
            },
            "content": {
                "type": "STRING",
                "description": "The content to write to the file."
            }
        },
        "required": ["path", "content"]
    }
}

read_directory_tool = {
    "name": "read_directory",
    "description": "Lists the contents of a directory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the directory to list."
            }
        },
        "required": ["path"]
    }
}

read_file_tool = {
    "name": "read_file",
    "description": "Reads the content of a file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to read."
            }
        },
        "required": ["path"]
    }
}

execute_command_tool = {
    "name": "execute_command",
    "description": "Execute a shell command on the user's system and return stdout, stderr, and exit code. Use for system administration, package management, git operations, file manipulation, and any CLI task. Examples: 'sudo apt update', 'ls -la /home', 'pip install numpy', 'git status'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": "The shell command to execute."
            },
            "working_directory": {
                "type": "STRING",
                "description": "Optional working directory to run the command in. Defaults to the project root."
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Max execution time in seconds. Defaults to 60."
            }
        },
        "required": ["command"]
    }
}

execute_code_tool = {
    "name": "execute_code",
    "description": "Execute Python or shell code in a sandboxed subprocess. Returns stdout, stderr, exit code, and execution time. Use for running scripts, data processing, calculations, or testing code snippets.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "code": {
                "type": "STRING",
                "description": "The source code to execute."
            },
            "language": {
                "type": "STRING",
                "description": "Programming language: 'python', 'shell', 'bash'. Defaults to 'python'."
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Max execution time in seconds. Defaults to 30."
            }
        },
        "required": ["code"]
    }
}

system_info_tool = {
    "name": "system_info",
    "description": "Get system information including OS details, CPU, memory usage, disk usage, and running processes. Use to understand the system you are operating on.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

recall_memory_tool = {
    "name": "recall_memory",
    "description": "Search your long-term memory for relevant facts, past conversations, and learned procedures. Use when you need to remember something about the user, a past interaction, or a workflow you learned before.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "What to search for in memory. Be descriptive."
            },
            "top_k": {
                "type": "INTEGER",
                "description": "Maximum number of results per memory tier. Defaults to 5."
            }
        },
        "required": ["query"]
    }
}

store_memory_tool = {
    "name": "store_memory",
    "description": "Explicitly save a fact, preference, or procedure to long-term memory. Use when the user tells you something important to remember, or when you learn a new workflow.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "content": {
                "type": "STRING",
                "description": "The fact, preference, or procedure to store."
            },
            "memory_type": {
                "type": "STRING",
                "description": "Type of memory: 'semantic' (facts/preferences), 'episodic' (event summaries), 'procedural' (workflows/how-to). Defaults to 'semantic'."
            }
        },
        "required": ["content"]
    }
}

read_document_tool = {
    "name": "read_document",
    "description": "Read the contents of a document file. Supports PDF, plain text, markdown, and common document formats. Use for reading notes, articles, reports, or any text-based file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "Absolute or relative path to the document file."
            },
            "max_pages": {
                "type": "INTEGER",
                "description": "For PDFs, maximum number of pages to read. Defaults to 50."
            }
        },
        "required": ["path"]
    }
}

study_document_tool = {
    "name": "study_document",
    "description": "Read a document and extract key facts, concepts, and procedures into long-term memory. Use for self-study -- when asked to learn from a PDF, article, or notes file. The extracted knowledge is stored permanently and can be recalled later.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "Path to the document to study."
            },
            "focus": {
                "type": "STRING",
                "description": "Optional focus area -- what to pay attention to when extracting knowledge."
            }
        },
        "required": ["path"]
    }
}

search_web_tool = {
    "name": "search_web",
    "description": "Perform a lightweight web search and return text results. Faster than full browser automation. Use for quick lookups, fact-checking, finding documentation, or getting current information.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search query."
            },
            "num_results": {
                "type": "INTEGER",
                "description": "Number of results to return. Defaults to 5."
            }
        },
        "required": ["query"]
    }
}

schedule_task_tool = {
    "name": "schedule_task",
    "description": "Create a scheduled task that runs automatically. Supports one-time, interval, and cron schedules. Examples: 'Run apt update every day at 3am', 'Remind me in 30 minutes', 'Check disk space every hour'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "A descriptive name for the task."
            },
            "schedule_type": {
                "type": "STRING",
                "description": "Schedule type: 'once' (one-time), 'interval' (recurring seconds), or 'cron' (cron expression like '0 3 * * *')."
            },
            "schedule_value": {
                "type": "STRING",
                "description": "For 'once': ISO datetime. For 'interval': seconds as string. For 'cron': cron expression (minute hour day month weekday)."
            },
            "tool_name": {
                "type": "STRING",
                "description": "The tool to execute when the task fires (e.g. 'execute_command')."
            },
            "tool_args": {
                "type": "STRING",
                "description": "JSON string of arguments for the tool (e.g. '{\"command\": \"apt update\"}')."
            }
        },
        "required": ["name", "schedule_type", "schedule_value", "tool_name"]
    }
}

add_monitor_tool = {
    "name": "add_monitor",
    "description": "Add a monitoring target to the heartbeat system. Monitors URLs (HTTP health checks), TCP ports, or running processes. Alerts when targets go down.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "A descriptive name for the monitoring target."
            },
            "target_type": {
                "type": "STRING",
                "description": "Type of monitoring: 'url' (HTTP check), 'tcp' (port check), or 'process' (process existence)."
            },
            "address": {
                "type": "STRING",
                "description": "Target address: URL for 'url' type, 'host:port' for 'tcp', or process name for 'process'."
            },
            "interval": {
                "type": "INTEGER",
                "description": "Check interval in seconds. Defaults to 60."
            }
        },
        "required": ["name", "target_type", "address"]
    }
}

create_alert_tool = {
    "name": "create_alert",
    "description": "Create an alert rule that triggers notifications when conditions are met. Supports threshold alerts (e.g. disk > 90%), status change alerts, and scheduled alerts.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "A descriptive name for the alert rule."
            },
            "condition_type": {
                "type": "STRING",
                "description": "Condition type: 'threshold' (min/max value check), 'status_change' (state transitions), or 'schedule' (cron-based)."
            },
            "condition_config": {
                "type": "STRING",
                "description": "JSON string of condition config. For threshold: '{\"key\": \"disk.used_percent\", \"max\": 90}'. For status_change: '{\"from\": \"up\", \"to\": \"down\"}'."
            },
            "action": {
                "type": "STRING",
                "description": "Action when triggered: 'notify' (store notification), 'log' (write to log), or 'webhook' (HTTP call)."
            }
        },
        "required": ["name", "condition_type", "condition_config"]
    }
}

shodan_search_tool = {
    "name": "shodan_search",
    "description": "Search Shodan for internet-connected devices and services matching a query. Returns IPs, ports, organizations, and banners. Requires SHODAN_API_KEY in environment.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Shodan search query (e.g. 'apache country:US', 'port:22 org:Google', 'hostname:example.com')."
            },
            "max_results": {
                "type": "INTEGER",
                "description": "Maximum number of results to return. Defaults to 10."
            }
        },
        "required": ["query"]
    }
}

shodan_host_tool = {
    "name": "shodan_host",
    "description": "Look up all known services, open ports, and banners for a specific IP address on Shodan.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "ip": {
                "type": "STRING",
                "description": "The IP address to look up."
            }
        },
        "required": ["ip"]
    }
}

nmap_scan_tool = {
    "name": "nmap_scan",
    "description": "Run an Nmap network scan and return structured results. Requires nmap to be installed on the system.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "Target IP, hostname, or CIDR range (e.g. '192.168.1.0/24', 'example.com')."
            },
            "ports": {
                "type": "STRING",
                "description": "Port specification (e.g. '22,80,443', '1-1000'). Defaults to top 1000 ports."
            },
            "scan_type": {
                "type": "STRING",
                "description": "Scan type: 'quick' (-F fast scan), 'version' (-sV service detection), 'os' (-O OS detection). Defaults to 'quick'."
            }
        },
        "required": ["target"]
    }
}

port_scan_tool = {
    "name": "port_scan",
    "description": "Fast TCP port scan using pure Python (no nmap required). Scans specified ports on a target host and reports which are open.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "host": {
                "type": "STRING",
                "description": "Target hostname or IP address."
            },
            "ports": {
                "type": "STRING",
                "description": "Ports to scan: comma-separated (e.g. '22,80,443') or range (e.g. '1-1024'). Defaults to common ports."
            },
            "timeout": {
                "type": "NUMBER",
                "description": "Connection timeout per port in seconds. Defaults to 1."
            }
        },
        "required": ["host"]
    }
}

mcp_connect_tool = {
    "name": "mcp_connect",
    "description": "Connect to an MCP (Model Context Protocol) server to access its tools. Supports stdio transport (local command) and HTTP transport (remote URL).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "A name to identify this MCP server connection."
            },
            "command": {
                "type": "STRING",
                "description": "For stdio transport: the command to start the MCP server (e.g. 'uvx mcp-server-sqlite --db-path ~/data.db')."
            },
            "url": {
                "type": "STRING",
                "description": "For HTTP transport: the URL of the MCP server (e.g. 'http://localhost:3000/mcp')."
            }
        },
        "required": ["name"]
    }
}

mcp_list_tools_tool = {
    "name": "mcp_list_tools",
    "description": "List all tools available from connected MCP servers.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

mcp_execute_tool = {
    "name": "mcp_execute",
    "description": "Execute a tool on a connected MCP server.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "server_name": {
                "type": "STRING",
                "description": "Name of the MCP server to execute on."
            },
            "tool_name": {
                "type": "STRING",
                "description": "Name of the tool to execute."
            },
            "arguments": {
                "type": "STRING",
                "description": "JSON string of arguments to pass to the tool."
            }
        },
        "required": ["server_name", "tool_name"]
    }
}

send_message_tool = {
    "name": "send_message",
    "description": "Send a message to a connected messaging platform (Telegram, Discord, etc.). Use to notify the user or communicate externally.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "platform": {
                "type": "STRING",
                "description": "Target platform: 'telegram', 'discord', etc."
            },
            "channel": {
                "type": "STRING",
                "description": "Channel or chat ID to send to."
            },
            "text": {
                "type": "STRING",
                "description": "Message text to send."
            }
        },
        "required": ["platform", "channel", "text"]
    }
}

list_platforms_tool = {
    "name": "list_platforms",
    "description": "List all connected messaging platforms and their status.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

plan_and_execute_tool = {
    "name": "plan_and_execute",
    "description": "Break a complex task into steps and execute them autonomously. Use for multi-step tasks that require planning, like 'upgrade my system and verify everything works' or 'scan my network and report vulnerabilities'. You will plan the steps, execute each one, and adapt if something fails.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "The complex task to plan and execute."
            },
            "steps": {
                "type": "STRING",
                "description": "Optional: pre-defined steps as a JSON array of strings. If not provided, you will auto-plan."
            }
        },
        "required": ["task"]
    }
}

tools_list = [{"function_declarations": [
    generate_cad_prototype_tool,
    write_file_tool,
    read_directory_tool,
    read_file_tool,
    execute_command_tool,
    execute_code_tool,
    system_info_tool,
    recall_memory_tool,
    store_memory_tool,
    read_document_tool,
    study_document_tool,
    search_web_tool,
    schedule_task_tool,
    add_monitor_tool,
    create_alert_tool,
    shodan_search_tool,
    shodan_host_tool,
    nmap_scan_tool,
    port_scan_tool,
    mcp_connect_tool,
    mcp_list_tools_tool,
    mcp_execute_tool,
    send_message_tool,
    list_platforms_tool,
    plan_and_execute_tool,
]}]


