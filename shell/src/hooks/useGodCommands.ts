import { useState, useCallback } from 'react';

interface CommandResult {
  success: boolean;
  output?: string;
  error?: string;
  data?: Record<string, unknown>;
}

interface UseGodCommandsReturn {
  sendCommand: (command: string) => Promise<CommandResult>;
  loading: boolean;
  lastResult: CommandResult | null;
  error: string | null;
}

/**
 * React hook that sends God Console commands to POST /api/v1/god/command
 * and returns the result.
 */
export function useGodCommands(): UseGodCommandsReturn {
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<CommandResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sendCommand = useCallback(
    async (command: string): Promise<CommandResult> => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch('/api/v1/god/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command }),
        });

        if (!res.ok) {
          const errText = await res.text().catch(() => `HTTP ${res.status}`);
          const result: CommandResult = {
            success: false,
            error: errText,
          };
          setLastResult(result);
          setError(errText);
          return result;
        }

        const data: CommandResult = await res.json();
        const result: CommandResult = {
          success: data.success ?? true,
          output: data.output,
          error: data.error,
          data: data.data,
        };
        setLastResult(result);
        return result;
      } catch (err: any) {
        // Network error — return a structured result instead of throwing
        const errMsg = err.message ?? String(err);
        const result: CommandResult = {
          success: false,
          error: `Network error: ${errMsg}`,
        };
        setLastResult(result);
        setError(errMsg);
        return result;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { sendCommand, loading, lastResult, error };
}

export default useGodCommands;
