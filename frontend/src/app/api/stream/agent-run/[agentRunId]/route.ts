import { NextRequest, NextResponse } from 'next/server';

// Ensure this route runs on Node runtime, not Edge
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Disable caching and compression for this route
export const revalidate = 0;

interface StreamEvent {
  type: 'token' | 'status' | 'delta' | 'done' | 'error';
  threadId: string;
  content: string;
  ts: number;
}

class SSEStream {
  private encoder = new TextEncoder();
  private controller: ReadableStreamDefaultController<Uint8Array> | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isClosed = false;

  constructor(private agentRunId: string) {}

  start(controller: ReadableStreamDefaultController<Uint8Array>) {
    this.controller = controller;
    this.startHeartbeat();
    this.sendEvent('open', { message: 'Stream connected' });
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (!this.isClosed && this.controller) {
        try {
          this.controller.enqueue(this.encoder.encode(': heartbeat\n\n'));
        } catch (error) {
          console.error('Failed to send heartbeat:', error);
          this.close();
        }
      }
    }, 15000); // Every 15 seconds
  }

  sendEvent(type: string, data: any) {
    if (this.isClosed || !this.controller) return;

    try {
      const eventData = JSON.stringify({
        type,
        threadId: this.agentRunId,
        content: data,
        ts: Date.now()
      });
      
      const message = `data: ${eventData}\n\n`;
      this.controller.enqueue(this.encoder.encode(message));
    } catch (error) {
      console.error('Failed to send event:', error);
      this.close();
    }
  }

  close() {
    if (this.isClosed) return;
    
    this.isClosed = true;
    
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.controller) {
      try {
        this.controller.enqueue(this.encoder.encode('event: close\ndata: stream-ended\n\n'));
        this.controller.close();
      } catch (error) {
        console.error('Error closing stream:', error);
      }
      this.controller = null;
    }
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { agentRunId: string } }
) {
  const { agentRunId } = params;
  
  if (!agentRunId) {
    return NextResponse.json({ error: 'Agent run ID is required' }, { status: 400 });
  }

  // Get auth token from query params or headers
  const url = new URL(request.url);
  const token = url.searchParams.get('token') || request.headers.get('authorization')?.replace('Bearer ', '');
  
  if (!token) {
    return NextResponse.json({ error: 'Authentication token required' }, { status: 401 });
  }

  // Create SSE stream
  const stream = new SSEStream(agentRunId);
  
  const readable = new ReadableStream({
    start(controller) {
      stream.start(controller);
      
      // Set up Redis subscription
      setupRedisSubscription(agentRunId, stream).catch(error => {
        console.error('Redis subscription error:', error);
        stream.sendEvent('error', { message: 'Stream connection failed' });
        stream.close();
      });
    },
    
    cancel() {
      stream.close();
    }
  });

  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    }
  });
}

async function setupRedisSubscription(agentRunId: string, stream: SSEStream) {
  // This would connect to Redis and subscribe to the agent run channel
  // For now, we'll simulate the connection
  console.log(`Setting up Redis subscription for agent run: ${agentRunId}`);
  
  // In a real implementation, this would:
  // 1. Connect to Redis using a dedicated subscriber connection
  // 2. Subscribe to `thread:${threadId}` channel
  // 3. Forward messages to the SSE stream
  // 4. Handle reconnection and cleanup
  
  // Simulate some test events
  setTimeout(() => {
    stream.sendEvent('status', { status: 'connecting' });
  }, 100);
  
  setTimeout(() => {
    stream.sendEvent('token', { content: 'Hello' });
  }, 1000);
  
  setTimeout(() => {
    stream.sendEvent('token', { content: ' world' });
  }, 1500);
  
  setTimeout(() => {
    stream.sendEvent('done', { message: 'Stream completed' });
    stream.close();
  }, 3000);
}
