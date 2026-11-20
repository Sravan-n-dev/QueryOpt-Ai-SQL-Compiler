import { useState, useCallback } from "react";
import { compileQuery } from "../utils/api";

export function useQueryEngine() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (query, mode) => {
    setLoading(true);
    setError(null);
    try {
      const data = await compileQuery(query, mode);
      setResult(data);
      if (!data.success) {
        setError({ stage: data.error_stage, message: data.error_message });
      }
      return data;
    } catch (err) {
      setError({ stage: "Network", message: err.message });
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, execute, clear };
}
