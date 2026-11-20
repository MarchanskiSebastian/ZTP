import { useMemo, useState } from 'react';
import { api, useApi } from '../api';
import { Alert, AsyncView, EmptyState, ErrorState, formatMoney, Loading } from '../components';

function ProductCard({ product, inCart, onAdded }) {
  const remaining = product.quantity - inCart; // what can still go into the cart
  const [qty, setQty] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const amount = Math.min(qty, Math.max(remaining, 1));

  async function add() {
    setBusy(true);
    setError(null);
    try {
      await api('/cart/items', { method: 'POST', body: { product_id: product.id, quantity: amount } });
      setQty(1);
      await onAdded();
    } catch (e) {
      setError(e);
      await onAdded(); // stock may have changed meanwhile: refresh
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card product">
      <span className="tag">{product.category.name}</span>
      <h3>{product.name}</h3>
      <div className="price">{formatMoney(product.price)}</div>
      <div className="muted">Na magazynie: {product.quantity} szt.{inCart > 0 && <> · w koszyku: <b>{inCart}</b></>}</div>
      <Alert error={error} onClose={() => setError(null)} />
      {remaining > 0 ? (
        <div className="add-row">
          <div className="stepper">
            <button onClick={() => setQty(amount - 1)} disabled={amount <= 1 || busy} aria-label="Mniej">−</button>
            <span>{amount}</span>
            <button onClick={() => setQty(amount + 1)} disabled={amount >= remaining || busy} aria-label="Więcej">+</button>
          </div>
          <button className="btn btn-primary" onClick={add} disabled={busy}>Dodaj do koszyka</button>
        </div>
      ) : (
        <div className="blocked">{product.quantity === 0 ? 'Brak w magazynie' : 'Cały dostępny stan jest już w koszyku'}</div>
      )}
    </div>
  );
}

export default function ProductsPage() {
  const products = useApi('/api/v1/products');
  const cart = useApi('/cart');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [onlyAvailable, setOnlyAvailable] = useState(false);

  const categories = useMemo(() => {
    const map = new Map((products.data || []).map((p) => [p.category.id, p.category.name]));
    return [...map].sort((a, b) => a[1].localeCompare(b[1]));
  }, [products.data]);

  const inCart = Object.fromEntries((cart.data?.items || []).map((i) => [i.product_id, i.quantity]));
  const refresh = () => Promise.all([products.reload(), cart.reload()]);

  if (cart.error) return <ErrorState error={cart.error} onRetry={cart.reload} />;
  if (!cart.data && !products.error) return <Loading />;

  return (
    <section>
      <div className="page-head">
        <h1>Produkty</h1>
        <div className="filters">
          <input placeholder="Szukaj po nazwie…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Kategoria">
            <option value="">Wszystkie kategorie</option>
            {categories.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
          <label className="check"><input type="checkbox" checked={onlyAvailable} onChange={(e) => setOnlyAvailable(e.target.checked)} /> Tylko dostępne</label>
        </div>
      </div>
      <AsyncView
        query={products}
        isEmpty={(list) => list.length === 0}
        empty={<EmptyState title="Brak produktów w sklepie" />}
      >
        {(list) => {
          const shown = list.filter((p) =>
            (!category || p.category.id === Number(category)) &&
            p.name.toLowerCase().includes(search.trim().toLowerCase()) &&
            (!onlyAvailable || p.quantity > 0));
          if (!shown.length) return <EmptyState title="Brak produktów spełniających filtry" />;
          return (
            <div className="grid">
              {shown.map((p) => <ProductCard key={p.id} product={p} inCart={inCart[p.id] || 0} onAdded={refresh} />)}
            </div>
          );
        }}
      </AsyncView>
    </section>
  );
}
