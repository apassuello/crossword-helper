import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for tracking real-time progress via Server-Sent Events (SSE).
 *
 * Connects to SSE endpoint and receives progress updates from backend operations.
 */
export function useSSEProgress() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle, running, complete, error
  const [message, setMessage] = useState('');
  const eventSourceRef = useRef(null);

  const connect = useCallback((taskId) => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create SSE connection
    const eventSource = new EventSource(`/api/progress/${taskId}`);
    eventSourceRef.current = eventSource;

    // Reset state
    setProgress(0);
    setStatus('running');
    setMessage('Starting...');

    // Handle progress events
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        setProgress(data.progress || 0);
        setMessage(data.message || 'Processing...');
        setStatus(data.status || 'running');

        // Close connection when complete or error
        if (data.status === 'complete' || data.status === 'error') {
          eventSource.close();
          eventSourceRef.current = null;
        }
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    // Handle errors
    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      setStatus('error');
      setMessage('Connection error');
      eventSource.close();
      eventSourceRef.current = null;
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    disconnect();
    setProgress(0);
    setStatus('idle');
    setMessage('');
  }, [disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    progress,
    status,
    message,
    connect,
    disconnect,
    reset
  };
}
