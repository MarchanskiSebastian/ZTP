import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, useApi, useIdempotentAction } from '../api';
import { Alert, AsyncView, EmptyState, formatMoney } from '../components';

export default function CartPage() {
  const cart = useApi('/cart');
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const checkout = useIdempotentAction(useCallback(
    (key) => api('/cart/checkout', { method: 'POST', headers: { 'Idempotency-Key': key } }), []));

  async function run(action) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e);
    } finally {
      await cart.reload(); // always show the server's state (e.g. stock changed in the meantime)
      setBusy(false);
    }
  }

  const setQuantity = (line, quantity) =>
    run(() => api(`/cart/items/${line.product_id}`, { method: 'PUT', body: { quantity } }));
  const remove = (line) => run(() => api(`/cart/items/${line.product_id}`, { method: 'DELETE' }));

  async function submitOrder() {
    setBusy(true);
    setError(null);
    try {
      const order = await checkout();
      navigate(`/orders/${order.id}`);
    } catch (e) {
      setError(e);
      await cart.reload();
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="page-head"><h1>Koszyk</h1></div>
      <Alert error={error} onClose={() => setError(null)} />
      <AsyncView
        query={cart}
        isEmpty={(c) => c.items.length === 0}
        empty={<EmptyState title="Koszyk jest pusty"><Link to="/products">Przejdź do produktów</Link></EmptyState>}
      >
        {(c) => (
          <div className="card">
            <table>
              <thead>
                <tr><th>Produkt</th><th>Cena</th><th>Ilość</th><th className="num">Wartość</th><th /></tr>
              </thead>
              <tbody>
                {c.items.map((line) => (
                  <tr key={line.product_id}>
                    <td>{line.name}<div className="muted">dostępne: {line.available} szt.</div></td>
                    <td>{formatMoney(line.unit_price)}</td>
                    <td>
                      <div className="stepper">
                        <button onClick={() => setQuantity(line, line.quantity - 1)} disabled={busy || line.quantity <= 1} aria-label="Mniej">−</button>
                        <span>{line.quantity}</span>
                        <button onClick={() => setQuantity(line, line.quantity + 1)} disabled={busy || line.quantity >= line.available} aria-label="Więcej">+</button>
                      </div>
                    </td>
                    <td className="num">{formatMoney(line.line_total)}</td>
                    <td className="num"><button className="btn btn-danger-ghost" onClick={() => remove(line)} disabled={busy}>Usuń</button></td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr><td colSpan={3}>Suma</td><td className="num total">{formatMoney(c.total)}</td><td /></tr>
              </tfoot>
            </table>
            <div className="actions">
              <Link to="/products" className="btn">Kontynuuj zakupy</Link>
              <button className="btn btn-primary" onClick={submitOrder} disabled={busy}>Zatwierdź zamówienie</button>
            </div>
          </div>
        )}
      </AsyncView>
    </section>
  );
}
