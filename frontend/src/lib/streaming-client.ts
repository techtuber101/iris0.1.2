import { createClient } from '@/lib/supabase/client';

// Get backend URL from environment variables
const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

interface StreamEvent {
  type: 'token' | 'status' | 'delta' | 'done' | 'error';
  threadId: string;
  content: string;
  ts: number;
}

interface StreamCallbacks {
  onMessage: (event: StreamEvent) => void;
  onError: (error: Error | string) => void;
  onClose: () => void;
  onReconnect?: (attempt: number) => void;
}

class StreamingClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isManuallyClosed = false;
  private agentRunId: string | null = null;

  constructor(private callbacks: StreamCallbacks) {}

  async connect(agentRunId: string): Promise<void> {
    if (this.eventSource) {
      this.disconnect();
    }

    this.agentRunId = agentRunId;
    this.isManuallyClosed = false;
    this.reconnectAttempts = 0;

    await this.createConnection();
  }

  private async createConnection(): Promise<void> {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.access_token) {
        throw new Error('No authentication token available');
      }

      const url = new URL(`${API_URL}/agent-run/${this.agentRunId}/stream`);
      url.searchParams.append('token', session.access_token);

      this.eventSource = new EventSource(url.toString());

      this.eventSource.onopen = () => {
        console.log(`[StreamingClient] Connected to stream for ${this.agentRunId}`);
        this.reconnectAttempts = 0; // Reset on successful connection
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.callbacks.onMessage(data);
        } catch (error) {
          console.error('[StreamingClient] Failed to parse message:', error);
          this.callbacks.onError('Failed to parse stream message');
        }
      };

      this.eventSource.onerror = (event) => {
        console.error(`[StreamingClient] EventSource error for ${this.agentRunId}:`, event);
        
        if (this.isManuallyClosed) {
          return;
        }

        // Attempt reconnection with exponential backoff
        this.scheduleReconnect();
      };

      // Handle custom events
      this.eventSource.addEventListener('close', () => {
        console.log(`[StreamingClient] Stream closed for ${this.agentRunId}`);
        this.callbacks.onClose();
        this.disconnect();
      });

    } catch (error) {
      console.error('[StreamingClient] Failed to create connection:', error);
      this.callbacks.onError(error instanceof Error ? error : String(error));
    }
  }

  private scheduleReconnect(): void {
    if (this.isManuallyClosed || this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error(`[StreamingClient] Max reconnection attempts reached for ${this.agentRunId}`);
        this.callbacks.onError('Max reconnection attempts reached');
      }
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
    
    console.log(`[StreamingClient] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      if (!this.isManuallyClosed) {
        this.callbacks.onReconnect?.(this.reconnectAttempts);
        this.createConnection();
      }
    }, delay);
  }

  disconnect(): void {
    this.isManuallyClosed = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    console.log(`[StreamingClient] Disconnected from stream for ${this.agentRunId}`);
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }
}

// Export a factory function for creating streaming clients
export function createStreamingClient(callbacks: StreamCallbacks): StreamingClient {
  return new StreamingClient(callbacks);
}

// Legacy compatibility - keep existing interface
export const streamAgent = (
  agentRunId: string,
  callbacks: {
    onMessage: (content: string) => void;
    onError: (error: Error | string) => void;
    onClose: () => void;
  }
) => {
  const streamingClient = createStreamingClient({
    onMessage: (event: StreamEvent) => {
      // Convert new event format to legacy format
      callbacks.onMessage(JSON.stringify(event));
    },
    onError: callbacks.onError,
    onClose: callbacks.onClose,
    onReconnect: (attempt) => {
      console.log(`[streamAgent] Reconnecting... attempt ${attempt}`);
    }
  });

  streamingClient.connect(agentRunId);

  return () => {
    streamingClient.disconnect();
  };
};
