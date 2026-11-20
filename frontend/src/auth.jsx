import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { api, setUnauthorizedHandler } from './api';
import { Loading } from './components';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = not checked yet, null = logged out

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    api('/auth/me').then(setUser, () => setUser(null)); // cookie is HttpOnly: ask the server who we are
  }, []);

  const login = useCallback(async (email, password) => {
    await api('/auth/login', { method: 'POST', body: { email, password } });
    setUser(await api('/auth/me'));
  }, []);

  const register = useCallback(async (email, password) => {
    await api('/auth/register', { method: 'POST', body: { email, password } });
    await login(email, password);
  }, [login]);

  const logout = useCallback(async () => {
    await api('/auth/logout', { method: 'POST' }).catch(() => {});
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

/** Protected route: without a session redirect to /login and come back afterwards. */
export function RequireAuth({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === undefined) return <Loading text="Sprawdzanie sesji…" />;
  if (user === null) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
