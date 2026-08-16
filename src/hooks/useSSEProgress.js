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
  const [data, setData] = useState(null); // payload of the latest event carrying data (e.g. final results)
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
    setData(null);

    // Handle progress events
    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);

        setProgress(eventData.progress || 0);
        setMessage(eventData.message || 'Processing...');
        // Capture the data payload BEFORE the status flips to complete/error,
        // so consumers reacting to status always see the final payload.
        if (eventData.data !== undefined && eventData.data !== null) {
          setData(eventData.data);
        }
        setStatus(eventData.status || 'running');

        // Close connection when complete or error
        if (eventData.status === 'complete' || eventData.status === 'error') {
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
    setData(null);
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
    data,
    connect,
    disconnect,
    reset
  };
}
