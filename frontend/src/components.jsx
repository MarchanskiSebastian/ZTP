import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from './auth';

const money = new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' });
export const formatMoney = (v) => money.format(v);
export const formatDate = (v) => (v ? new Date(v).toLocaleString('pl-PL') : '—');

export function Loading({ text = 'Ładowanie…' }) {
  return <div className="state"><div className="spinner" />{text}</div>;
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state state-error" role="alert">
      <strong>Nie udało się pobrać danych</strong>
      <span>{error?.message}</span>
      {onRetry && <button className="btn" onClick={onRetry}>Spróbuj ponownie</button>}
    </div>
  );
}

export function EmptyState({ title, children }) {
  return <div className="state state-empty"><strong>{title}</strong>{children}</div>;
}

/** Renders loading / error / empty / content for one useApi() result. */
export function AsyncView({ query, isEmpty = () => false, empty, children }) {
  if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />;
  if (!query.data) return <Loading />;
  if (isEmpty(query.data)) return empty;
  return children(query.data);
}

export function Alert({ error, onClose }) {
  if (!error) return null;
  return (
    <div className="alert" role="alert">
      {error.message}
      {onClose && <button className="link" onClick={onClose} aria-label="Zamknij">✕</button>}
    </div>
  );
}

const STATUS = { PENDING: 'Oczekujące', COMPLETED: 'Zakończone', CANCELLED: 'Anulowane' };
export const StatusBadge = ({ status }) => <span className={`badge badge-${status}`}>{STATUS[status]}</span>;

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="nav">
        <span className="brand">ZTP Sklep</span>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/products">Produkty</NavLink>
          <NavLink to="/cart">Koszyk</NavLink>
          <NavLink to="/orders">Zamówienia</NavLink>
        </nav>
        <span className="who">{user.email}</span>
        <button className="btn btn-ghost" onClick={logout}>Wyloguj</button>
      </header>
      <main><Outlet /></main>
    </>
  );
}
