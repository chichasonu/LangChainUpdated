## python .\main.py > output.log 2>&1 


# A2A Weather Agent with Push Notifications

An AI-powered weather assistant built with Google ADK and the A2A (Agent-to-Agent) protocol. This agent provides weather information through a JSON-RPC interface with task lifecycle management and push notification support.

## Features

- **A2A Protocol Compliance**: Full support for A2A JSON-RPC methods (SendMessage, GetTask, ListTasks, CancelTask)
- **Google ADK Integration**: Built on Google's Agent Development Kit with Gemini 2.5 Flash model
- **Task Lifecycle Management**: Track task status from submission to completion
- **Push Notifications**: Enabled for real-time task updates (SSE support can be added)
- **Custom Task Store**: In-memory task storage with LRU eviction and TTL support
- **History Optimization**: Automatically clears task history to reduce storage overhead
- **Weather Tool**: Mock weather service (easily replaceable with real API)

## Prerequisites

- Python 3.14+
- pip or uv package manager
- Google Cloud API key (for Gemini model)

## Installation

1. **Clone the repository**:
   ```bash
   cd C:\Users\<user>\PycharmProjects\LangChainUpdated\updatedlangchain
   ```

2. **Install dependencies**:
   ```bash
   # Using pip
   pip install -r ../requirements.txt
   pip install a2a-sdk[http-server]>=1.2.2 google-adk>=2.11.0 uvicorn>=0.54.0
   
   # Or using uv (recommended)
   uv sync
   ```

3. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your-google-cloud-api-key
   ```

## Configuration

### Server Settings

Edit `main.py` to customize:
- **Host**: `HOST = "localhost"` (line 18)
- **Port**: `PORT = 8000` (line 19)
- **Agent Model**: `model="gemini-2.5-flash"` (line 53)
- **Task Store**: `max_tasks=1000, task_ttl_seconds=3600` (line 92)

### Task Store Configuration

Located in `custom_inmemory_task_store.py`:
- `max_tasks`: Maximum number of tasks to store (default: 1000)
- `task_ttl_seconds`: Time-to-live for tasks in seconds (default: 3600 = 1 hour)
- LRU eviction when max_tasks is exceeded
- TTL-based expiration of old tasks

## Running the Server

1. **Activate virtual environment** (if using):
   ```powershell
   .\.venv\Scripts\activate
   ```

2. **Navigate to the project directory**:
   ```powershell
   cd .\updatedlangchain\
   ```

3. **Start the server**:
   ```powershell
   python main.py
   ```

   Or run in background with logging:
   ```powershell
   python main.py > output.log 2>&1
   ```

4. **Verify the server is running**:
   - Agent Card: http://localhost:8000/.well-known/agent-card.json
   - JSON-RPC Endpoint: http://localhost:8000/api/v1/jsonrpc

## API Endpoints

### 1. Agent Card

**GET** `http://localhost:8000/.well-known/agent-card.json`

Returns the agent's metadata, capabilities, and interface information.

### 2. JSON-RPC Endpoint

**POST** `http://localhost:8000/api/v1/jsonrpc`

**Headers**:


#### Supported Methods

| Method | Description |
|--------|-------------|
| `SendMessage` | Submit a new task or message |
| `GetTask` | Retrieve task status by ID |
| `ListTasks` | List all tasks with pagination |
| `CancelTask` | Cancel a running task |
| `SubscribeToTask` | Subscribe to task updates (streaming) |
| `SendStreamingMessage` | Send message with streaming response |

## Usage Examples

### Submit a Task (SendMessage)

```json
POST http://localhost:8000/api/v1/jsonrpc
Content-Type: application/json
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "text": "What's the weather in San Francisco?"
        }
      ]
    }
  }
}

{
  "jsonrpc": "2.0",
  "result": {
    "id": "generated-task-id-here",
    "status": "in_progress",
    "history": []
  },
  "id": 1
}

### Get Task Status (GetTask)

```json
POST http://localhost:8000/api/v1/jsonrpc
Content-Type: application/json
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "GetTask",
  "params": {
    "taskId": "generated-task-id-here"
  }
}

{
  "jsonrpc": "2.0",
  "result": {
    "id": "generated-task-id-here",
    "status": "completed",
    "result": {
      "text": "The weather in San Francisco is sunny with a temperature of 72°F."
    },
    "history": [
      {
        "role": "user",
        "parts": [
          {
            "text": "What's the weather in San Francisco?"
          }
        ]
      },
      {
        "role": "model",
        "parts": [
          {
            "text": "The weather in San Francisco is sunny with a temperature of 72°F."
          }
        ]
      }
    ]
  },
  "id": 2
}


POST http://localhost:8000/api/v1/jsonrpc
Content-Type: application/json
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "ListTasks",
  "params": {
    "pageSize": 10
  }
}

{
  "jsonrpc": "2.0",
  "result": {
    "tasks": [
      {
        "id": "generated-task-id-here",
        "status": "completed",
        "result": {
          "text": "The weather in San Francisco is sunny with a temperature of 72°F."
        },
        "history": [
          {
            "role": "user",
            "parts": [
              {
                "text": "What's the weather in San Francisco?"
              }
            ]
          },
          {
            "role": "model",
            "parts": [
              {
                "text": "The weather in San Francisco is sunny with a temperature of 72°F."
              }
            ]
          }
        ]
      }
    ],
    "nextPageToken": null
  },
  "id": 3
}