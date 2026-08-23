import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

/**
 * Hook for tracking real-time progress via Server-Sent Events (SSE).
 *
 * Connects to SSE endpoint and receives progress updates from backend operations.
 *
 * The stream itself is opened by `api.openProgress`, which owns the EventSource
 * and its JSON parsing — this hook holds no endpoint knowledge (issue #12).
 */
export function useSSEProgress() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle, running, complete, error
  const [message, setMessage] = useState('');
  const [data, setData] = useState(null); // payload of the latest event carrying data (e.g. final results)
  const streamRef = useRef(null);

  const connect = useCallback((taskId) => {
    // Close existing connection if any
    if (streamRef.current) {
      streamRef.current.close();
    }

    // Reset state
    setProgress(0);
    setStatus('running');
    setMessage('Starting...');
    setData(null);

    const stream = api.openProgress(taskId, {
      onEvent: (eventData) => {
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
          stream.close();
          streamRef.current = null;
        }
      },
      onError: (error) => {
        console.error('SSE error:', error);
        setStatus('error');
        setMessage('Connection error');
        stream.close();
        streamRef.current = null;
      },
    });

    streamRef.current = stream;

    return () => {
      stream.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
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
      if (streamRef.current) {
        streamRef.current.close();
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
