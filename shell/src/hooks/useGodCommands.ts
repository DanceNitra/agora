import { useState, useCallback } from 'react';

interface GodApiResponse {
  parsed_command: string;
  args: Record<string, unknown>;
  result: string;
  success: boolean;
}

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
          const result: CommandResult = { success: false, error: errText };
          setLastResult(result);
          setError(errText);
          return result;
        }

        const data: GodApiResponse = await res.json();
        const result: CommandResult = {
          success: data.success,
          output: data.result,
          error: data.success ? undefined : data.result,
          data: data.args as Record<string, unknown>,
        };
        setLastResult(result);
        return result;
      } catch (err: any) {
        const errMsg = err.message ?? String(err);
        const result: CommandResult = { success: false, error: `Network error: ${errMsg}` };
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
