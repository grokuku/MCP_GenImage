# MCP GenImage: Asynchronous Tool Call Integration Guide

## 1. Objective

To handle long-running tasks like image generation without causing client-side timeouts, the `generate_image` tool uses the standard **asynchronous streaming model** of the Model Context Protocol (MCP).

This guide details the exact sequence of events and message formats your client (the bot) must implement to be compatible with this asynchronous workflow.

---

## 2. High-Level Workflow

The interaction for a single `generate_image` call will now follow these steps:

1.  **Request Initiation:** Your client sends a standard `tools/call` request to the `/mcp` endpoint.
2.  **Immediate Acknowledgement:** The server immediately validates the request, initiates the task in the background, and replies with a `stream/start` message. This message contains a unique WebSocket URL for your client to connect to for updates.
3.  **WebSocket Connection:** Your client must immediately connect to the provided WebSocket URL.
4.  **Receiving Updates:** Your client listens for incoming messages on the WebSocket connection. The server will send a final result or an error.
5.  **Final Result:** The server sends a `stream/chunk` message containing the generated image URL (on success) or an error object (on failure).
6.  **Stream Termination:** The server sends a `stream/end` message to signal that the task is complete and no more messages will be sent.
7.  **Connection Closure:** Your client closes the WebSocket connection.

---

## 3. Detailed Protocol Specification

### Step 1: `tools/call` Request (Client -> Server)

This step remains unchanged. Your client sends the tool call request as before.

**Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "generate_image",
        "arguments": {
            "prompt": "A majestic dragon flying over a medieval castle",
            "style_names": ["Fantasy Art"]
        }
    },
    "id": "req-client-123"
}
```
### Step 2: `tools/call` Initial Response (Server -> Client)

The server's immediate response will **not** contain the image. Instead, it will be a JSON-RPC notification acknowledging the task and providing connection details for the stream.

**Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "stream/start",
    "params": {
        "stream_id": "d1eed89c-d2ff-427e-b5d2-cd004a668935",
        "ws_url": "ws://your_server_url:8001/ws/stream/d1eed89c-d2ff-427e-b5d2-cd004a668935"
    },
    "id": "req-client-123"
}
```    **Client Actions:**
- Upon receiving this response with `method: "stream/start"`, parse the `ws_url` from the `params`.
- You may want to display a text message to the user like "Image generation has been queued. I will send you the result when it's ready."
- Immediately proceed to Step 3.

### Step 3: Establish WebSocket Connection (Client -> Server)

Your client must initiate a WebSocket connection to the URL provided in `ws_url`. This connection should be maintained until a `stream/end` message is received.

### Step 4: Receive WebSocket Messages (Server -> Client)

Once connected, your client will receive a JSON message from the server. This message is a JSON-RPC notification (it has a `method` but no `id`).

#### A. Final Success Message

When the image is successfully generated, the server will send a `stream/chunk` message containing a `result` object, which in turn holds the standard `content` array.

**Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "stream/chunk",
    "params": {
        "stream_id": "d1eed89c-d2ff-427e-b5d2-cd004a668935",
        "result": {
            "content": [
                {
                    "type": "image",
                    "source": "http://your_server_url:8001/outputs/some-unique-id.png"
                }
            ]
        }
    }
}
```
**Client Actions:**
- Parse the message and check for the existence of the `result` key in `params`.
- Extract the image URL from `result.content[0].source`.
- Display the image to the user.

#### B. Final Failure Message

If the image generation fails, the server will send a `stream/chunk` message containing a standard JSON-RPC `error` object.

**Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "stream/chunk",
    "params": {
        "stream_id": "d1eed89c-d2ff-427e-b5d2-cd004a668935",
        "error": {
            "code": -32000,
            "message": "Service error: No active ComfyUI server is compatible with render type 'SomeType'."
        }
    }
}
```
**Client Actions:**
- Parse the message and check for the existence of the `error` key in `params`.
- Display the `error.message` to the user.

### Step 5: Receive Stream End Message (Server -> Client)

After the final result (either success or failure) has been sent, the server will send a `stream/end` message to signify the end of the transaction.

**Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "stream/end",
    "params": {
        "stream_id": "d1eed89c-d2ff-427e-b5d2-cd004a668935"
    }
}
```
**Client Actions:**
- Upon receiving this message, you must close the WebSocket connection. The `stream_id` is now invalid.

---

## 4. Implementation Checklist for the Client

- [ ] Can your client parse the initial `tools/call` response to identify a `method` equal to `stream/start`?
- [ ] Can your client extract the `ws_url` from the `params` of this response?
- [ ] Does your client have a library/capability to establish a WebSocket connection?
- [ ] Can your client listen for and parse incoming JSON messages on the WebSocket?
- [ ] Can your client handle `stream/chunk` messages by checking for `params.result` (for success) or `params.error` (for failure)?
- [ ] Does your client correctly identify the `stream/end` message and terminate the WebSocket connection?