# Streaming Implementation Guide

This document explains the end-to-end streaming implementation that enables real-time updates without manual refreshes.

## Architecture Overview

The streaming pipeline follows this flow:
```
Python Worker → Redis (pub) → API Route (sub) → Browser (SSE)
```

## Key Components

### 1. Redis Configuration (`backend/core/services/redis_client.py`)

- **Consistent Encoding**: Both sync and async clients use `decode_responses=True` for string mode
- **Dedicated Connections**: Separate publisher and subscriber connections for pub/sub operations
- **New Functions**:
  - `get_publisher()`: Creates dedicated publisher client
  - `get_subscriber()`: Creates dedicated subscriber client  
  - `publish_to_channel()`: Publishes with automatic cleanup
  - `create_dedicated_pubsub()`: Creates dedicated pubsub connection

### 2. Backend Streaming Route (`backend/core/agent_runs.py`)

- **Proper SSE Headers**: 
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache, no-transform`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- **Dedicated Redis Subscriber**: Uses separate connection for streaming
- **Dual Channel Subscription**: 
  - `agent_run:{id}:new_response` (legacy compatibility)
  - `thread:{threadId}` (direct streaming)
- **Heartbeat**: Sends `:keepalive` every 15 seconds
- **Graceful Cleanup**: Properly unsubscribes and closes connections

### 3. Python Worker Updates (`backend/run_agent_background.py`)

- **Incremental Publishing**: Uses `publish_to_channel()` for immediate streaming
- **Dedicated Publisher**: Each publish operation gets its own connection
- **Consistent JSON**: All messages published as UTF-8 JSON strings

### 4. Core Agent Execution (`backend/core/run.py`)

- **Direct Streaming**: Publishes events directly to `thread:{threadId}` channel
- **Real-time Events**: Each token/chunk published immediately as it's generated
- **Event Schema**: Standardized format with `type`, `threadId`, `content`, `ts`

### 5. Frontend Streaming Client (`frontend/src/lib/streaming-client.ts`)

- **Auto-reconnect**: Exponential backoff with configurable max attempts
- **EventSource**: Native browser SSE support with proper error handling
- **Connection Management**: Automatic cleanup and reconnection logic
- **Legacy Compatibility**: Maintains existing `streamAgent` interface

### 6. React Hook Updates (`frontend/src/hooks/useAgentStream.ts`)

- **New Client Integration**: Uses `createStreamingClient` for improved reliability
- **Better Error Handling**: Distinguishes between expected and unexpected errors
- **Reconnection Feedback**: Shows user-friendly reconnection messages
- **Proper Cleanup**: Ensures streams are closed when components unmount

### 7. Next.js Configuration (`frontend/next.config.ts`)

- **Compression Disabled**: `compress: false` globally
- **Stream Headers**: Custom headers for `/api/stream/*` routes
- **Cache Control**: Explicit no-cache headers for streaming endpoints

## Testing

### Local Testing

1. **Run the test script**:
   ```bash
   python test_streaming.py
   ```

2. **Manual browser testing**:
   - Open browser dev tools → Network tab
   - Start an agent run
   - Look for the stream request in Network tab
   - Check "Messages" tab to see SSE events flowing

3. **Redis monitoring**:
   ```bash
   redis-cli monitor
   ```
   Watch for pub/sub activity on `thread:*` channels

### Production Testing

1. **Check logs**: Look for streaming-related log messages
2. **Monitor connections**: Ensure Redis connections are properly closed
3. **Test reconnection**: Simulate network interruptions
4. **Verify encoding**: Test with non-ASCII content

## Event Schema

All streaming events follow this schema:
```typescript
interface StreamEvent {
  type: 'token' | 'status' | 'delta' | 'done' | 'error';
  threadId: string;
  content: string | object;
  ts: number; // Unix timestamp in milliseconds
}
```

## Troubleshooting

### Common Issues

1. **"Must refresh to see updates"**
   - Check Redis encoding consistency
   - Verify SSE headers are set correctly
   - Ensure no compression middleware is active

2. **Connection drops frequently**
   - Check network stability
   - Verify heartbeat is working (look for `:keepalive` in dev tools)
   - Check Redis connection limits

3. **Messages not appearing**
   - Verify Redis pub/sub is working
   - Check channel names match between publisher and subscriber
   - Ensure JSON parsing is working correctly

### Debug Commands

```bash
# Check Redis connections
redis-cli client list

# Monitor Redis activity
redis-cli monitor

# Test Redis pub/sub manually
redis-cli publish "thread:test" '{"type":"test","content":"hello"}'
```

## Performance Considerations

- **Redis Connections**: Each stream creates dedicated connections that are properly cleaned up
- **Memory Usage**: EventSource connections are limited by browser (typically 6 per domain)
- **Log Volume**: Reduced logging to prevent Railway rate limiting
- **Heartbeat**: 15-second intervals to keep connections alive without excessive overhead

## Security

- **Authentication**: JWT tokens validated before stream creation
- **Channel Isolation**: Each thread uses its own channel (`thread:{threadId}`)
- **Connection Limits**: Proper cleanup prevents connection leaks
- **Input Validation**: All published messages are JSON-validated
