import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api';
import { AsyncView, EmptyState, formatDate, formatMoney, StatusBadge } from '../components';

const FILTERS = [['', 'Wszystkie'], ['PENDING', 'Oczekujące'], ['COMPLETED', 'Zakończone'], ['CANCELLED', 'Anulowane']];

export function OrdersTable({ orders }) {
  return (
    <table>
      <thead><tr><th>Numer</th><th>Data</th><th>Status</th><th className="num">Suma</th></tr></thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id}>
            <td><Link to={`/orders/${o.id}`}>{o.number}</Link></td>
            <td>{formatDate(o.created_at)}</td>
            <td><StatusBadge status={o.status} /></td>
            <td className="num">{formatMoney(o.total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function OrdersPage() {
  const orders = useApi('/orders');
  const [status, setStatus] = useState('');
  return (
    <section>
      <div className="page-head">
        <h1>Historia zamówień</h1>
        <div className="tabs">
          {FILTERS.map(([value, label]) => (
            <button key={value} className={status === value ? 'active' : ''} onClick={() => setStatus(value)}>{label}</button>
          ))}
        </div>
      </div>
      <AsyncView
        query={orders}
        isEmpty={(list) => list.length === 0}
        empty={<EmptyState title="Nie masz jeszcze zamówień"><Link to="/products">Zacznij zakupy</Link></EmptyState>}
      >
        {(list) => {
          const shown = list.filter((o) => !status || o.status === status);
          return shown.length
            ? <div className="card"><OrdersTable orders={shown} /></div>
            : <EmptyState title="Brak zamówień o tym statusie" />;
        }}
      </AsyncView>
    </section>
  );
}
