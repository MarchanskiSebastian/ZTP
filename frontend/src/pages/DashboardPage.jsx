import { Link } from 'react-router-dom';
import { useApi } from '../api';
import { AsyncView, EmptyState, formatMoney } from '../components';
import { OrdersTable } from './OrdersPage';

function Stat({ label, value, tone }) {
  return <div className={`card stat ${tone || ''}`}><span>{label}</span><strong>{value}</strong></div>;
}

export default function DashboardPage() {
  const dashboard = useApi('/bff/dashboard'); // one BFF request for the whole view
  return (
    <AsyncView query={dashboard}>
      {(d) => (
        <section>
          <div className="page-head"><h1>Witaj, {d.user.email}</h1></div>
          <div className="stats">
            <Stat label="Wszystkie zamówienia" value={d.orders.total} />
            <Stat label="Oczekujące" value={d.orders.pending} tone="PENDING" />
            <Stat label="Zakończone" value={d.orders.completed} tone="COMPLETED" />
            <Stat label="Anulowane" value={d.orders.cancelled} tone="CANCELLED" />
            <Stat label="Wydano (zakończone)" value={formatMoney(d.orders.completed_value)} />
            <Stat label="W koszyku" value={`${d.cart.items} szt. · ${formatMoney(d.cart.total)}`} />
          </div>
          <div className="columns">
            <div>
              <h2>Ostatnie zamówienia</h2>
              {d.recent_orders.length
                ? <div className="card"><OrdersTable orders={d.recent_orders} /></div>
                : <EmptyState title="Brak zamówień"><Link to="/products">Przejdź do produktów</Link></EmptyState>}
            </div>
            <div>
              <h2>Ostatnio anulowane</h2>
              {d.recent_cancelled.length
                ? <div className="card"><OrdersTable orders={d.recent_cancelled} /></div>
                : <EmptyState title="Brak anulowanych zamówień" />}
            </div>
          </div>
        </section>
      )}
    </AsyncView>
  );
}
