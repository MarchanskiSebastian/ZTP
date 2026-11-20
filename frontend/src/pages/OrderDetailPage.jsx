import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, useApi, useIdempotentAction } from '../api';
import { Alert, AsyncView, formatDate, formatMoney, StatusBadge } from '../components';

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const order = useApi(`/orders/${orderId}`);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const post = useCallback((action) => (key) =>
    api(`/orders/${orderId}/${action}`, { method: 'POST', headers: { 'Idempotency-Key': key } }), [orderId]);
  const complete = useIdempotentAction(post('complete'));
  const cancel = useIdempotentAction(post('cancel'));

  async function run(action) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e);
    } finally {
      await order.reload(); // status shown is always the server's
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="page-head"><Link to="/orders">← Historia zamówień</Link></div>
      <AsyncView query={order}>
        {(o) => {
          const pending = o.status === 'PENDING'; // complete / cancel allowed only for PENDING
          return (
            <div className="card">
              <div className="order-head">
                <div>
                  <h1>{o.number}</h1>
                  <div className="muted">Złożone: {formatDate(o.created_at)}
                    {o.completed_at && <> · zakończone: {formatDate(o.completed_at)}</>}
                    {o.cancelled_at && <> · anulowane: {formatDate(o.cancelled_at)}</>}
                  </div>
                </div>
                <StatusBadge status={o.status} />
              </div>
              <Alert error={error} onClose={() => setError(null)} />
              <table>
                <thead><tr><th>Produkt</th><th>Cena</th><th>Ilość</th><th className="num">Wartość</th></tr></thead>
                <tbody>
                  {o.items.map((i) => (
                    <tr key={i.product_id}>
                      <td>{i.product_name}</td><td>{formatMoney(i.unit_price)}</td><td>{i.quantity}</td>
                      <td className="num">{formatMoney(i.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot><tr><td colSpan={3}>Suma</td><td className="num total">{formatMoney(o.total)}</td></tr></tfoot>
              </table>
              <div className="actions">
                {!pending && <span className="muted">Zamówienie ma status końcowy – nie można go już zmienić.</span>}
                <button className="btn btn-danger" disabled={!pending || busy}
                        onClick={() => window.confirm('Anulować zamówienie? Produkty wrócą na magazyn.') && run(cancel)}>
                  Anuluj zamówienie
                </button>
                <button className="btn btn-primary" disabled={!pending || busy} onClick={() => run(complete)}>
                  Zakończ zamówienie
                </button>
              </div>
            </div>
          );
        }}
      </AsyncView>
    </section>
  );
}
