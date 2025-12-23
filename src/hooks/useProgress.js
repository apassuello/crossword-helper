import { useState, useEffect, useCallback } from 'react';

/**
 * Hook for managing progress state with simulated increments
 * Provides realistic progress feedback even when backend doesn't send updates
 */
export function useProgress(estimatedDuration = 5000) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle, running, complete, error
  const [message, setMessage] = useState('');

  const start = useCallback((initialMessage = 'Starting...') => {
    setProgress(0);
    setStatus('running');
    setMessage(initialMessage);
  }, []);

  const update = useCallback((newProgress, newMessage) => {
    setProgress(Math.min(newProgress, 100));
    if (newMessage) setMessage(newMessage);
  }, []);

  const complete = useCallback((finalMessage = 'Complete!') => {
    setProgress(100);
    setStatus('complete');
    setMessage(finalMessage);
  }, []);

  const error = useCallback((errorMessage = 'An error occurred') => {
    setStatus('error');
    setMessage(errorMessage);
  }, []);

  const reset = useCallback(() => {
    setProgress(0);
    setStatus('idle');
    setMessage('');
  }, []);

  // Simulate progress increments when running
  useEffect(() => {
    if (status !== 'running' || progress >= 95) return;

    const increment = () => {
      setProgress(prev => {
        // Slow down as we approach completion
        const rate = prev < 50 ? 2 : prev < 80 ? 1 : 0.5;
        return Math.min(prev + rate, 95); // Never go to 100 automatically
      });
    };

    const interval = setInterval(increment, estimatedDuration / 50);
    return () => clearInterval(interval);
  }, [status, progress, estimatedDuration]);

  return {
    progress,
    status,
    message,
    start,
    update,
    complete,
    error,
    reset
  };
}

/**
 * Simulate progress for pattern search
 */
export function usePatternSearchProgress() {
  const progress = useProgress(2000); // 2 second estimated duration

  const startSearch = useCallback((pattern, wordlists, algorithm) => {
    const wordlistCount = wordlists.length;
    const algorithmName = algorithm === 'trie' ? 'Trie (Fast)' : 'Regex';

    progress.start(`Searching for "${pattern}" using ${algorithmName} algorithm...`);

    // Simulate scanning through wordlists
    setTimeout(() => {
      progress.update(30, `Scanning ${wordlistCount} wordlist(s)...`);
    }, 200);

    setTimeout(() => {
      progress.update(60, `Processing matches...`);
    }, 600);

    setTimeout(() => {
      progress.update(90, `Sorting results...`);
    }, 1000);
  }, [progress]);

  return { ...progress, startSearch };
}

/**
 * Simulate progress for autofill
 */
export function useAutofillProgress() {
  const progress = useProgress(30000); // 30 second estimated duration

  const startAutofill = useCallback((totalSlots, algorithm) => {
    const algorithmName = algorithm === 'trie' ? 'Trie (Fast)' : 'Regex';

    progress.start(`Initializing autofill with ${algorithmName} algorithm...`);

    // Simulate filling slots
    let slotsFilled = 0;
    const updateInterval = setInterval(() => {
      if (slotsFilled < totalSlots * 0.8) {
        slotsFilled += Math.ceil(totalSlots * 0.1);
        const percent = Math.round((slotsFilled / totalSlots) * 100);
        progress.update(
          percent,
          `Filling slots: ${Math.min(slotsFilled, totalSlots)}/${totalSlots}`
        );
      }
    }, 2000);

    // Clean up on complete
    setTimeout(() => clearInterval(updateInterval), 30000);
  }, [progress]);

  return { ...progress, startAutofill };
}

/**
 * Simulate progress for export
 */
export function useExportProgress() {
  const progress = useProgress(1500); // 1.5 second estimated duration

  const startExport = useCallback((format) => {
    progress.start(`Preparing ${format.toUpperCase()} export...`);

    const steps = [
      { at: 300, progress: 25, message: 'Formatting data...' },
      { at: 600, progress: 50, message: 'Generating file...' },
      { at: 900, progress: 75, message: 'Finalizing...' },
      { at: 1200, progress: 95, message: 'Ready to download!' }
    ];

    steps.forEach(step => {
      setTimeout(() => {
        progress.update(step.progress, step.message);
      }, step.at);
    });
  }, [progress]);

  return { ...progress, startExport };
}