import { useCallback, useEffect, useRef, useState } from 'react';

const BASE = '/backend';

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

function errorMessage(data, status) {
  const detail = data?.detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg).join('; '); // FastAPI 422 validation list
  return detail || `Błąd serwera (${status}).`;
}

/** Shared client for every request: JSON in/out, cookie session, one error type. */
export async function api(path, { method = 'GET', body, headers = {} } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: 'include', // send/receive the auth_token cookie
      headers: { ...(body !== undefined && { 'Content-Type': 'application/json' }), ...headers },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Brak połączenia z serwerem.');
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/login') onUnauthorized(); // session expired -> back to login
    throw new ApiError(res.status, errorMessage(data, res.status));
  }
  return data;
}

/** GET with loading / error / data state and reload(). Old data stays visible while reloading. */
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      setState({ data: await api(path), error: null, loading: false });
    } catch (error) {
      setState({ data: null, error, loading: false });
    }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}

/**
 * Runs `fn(idempotencyKey)`. The key is generated once per user action and reused when the request
 * failed without an answer (network / 5xx), so a retry can never execute the operation twice.
 */
export function useIdempotentAction(fn) {
  const key = useRef(null);
  return useCallback(async (...args) => {
    key.current ??= crypto.randomUUID();
    try {
      const result = await fn(key.current, ...args);
      key.current = null;
      return result;
    } catch (e) {
      if (e.status && e.status < 500) key.current = null; // the server answered: next click is a new action
      throw e;
    }
  }, [fn]);
}
