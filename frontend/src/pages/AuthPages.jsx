import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { Alert } from '../components';
import { validateCredentials } from '../validation';

function Field({ label, error, ...props }) {
  return (
    <label className="field">
      {label}
      <input {...props} aria-invalid={!!error} className={error ? 'invalid' : ''} />
      {error && <small className="field-error">{error}</small>}
    </label>
  );
}

function AuthForm({ register }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const from = useLocation().state?.from || '/';
  const [form, setForm] = useState({ email: '', password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (auth.user) return <Navigate to={from} replace />;

  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    const found = validateCredentials(form, { register });
    setErrors(found);
    setApiError(null);
    if (Object.keys(found).length) return; // invalid form: no request is sent
    setBusy(true);
    try {
      await (register ? auth.register : auth.login)(form.email.trim(), form.password);
      navigate(from, { replace: true });
    } catch (err) {
      setApiError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit} noValidate>
        <h1>{register ? 'Rejestracja' : 'Logowanie'}</h1>
        <Alert error={apiError} />
        <Field label="E-mail" type="email" value={form.email} onChange={set('email')} error={errors.email} autoComplete="email" />
        <Field label="Hasło" type="password" value={form.password} onChange={set('password')} error={errors.password}
               autoComplete={register ? 'new-password' : 'current-password'} />
        {register && (
          <Field label="Powtórz hasło" type="password" value={form.confirm} onChange={set('confirm')} error={errors.confirm}
                 autoComplete="new-password" />
        )}
        {register && <small className="hint">Min. 8 znaków, co najmniej jedna litera i cyfra.</small>}
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Proszę czekać…' : register ? 'Załóż konto' : 'Zaloguj'}</button>
        <p className="switch">
          {register ? <>Masz konto? <Link to="/login">Zaloguj się</Link></> : <>Nie masz konta? <Link to="/register">Zarejestruj się</Link></>}
        </p>
      </form>
    </div>
  );
}

export const LoginPage = () => <AuthForm />;
export const RegisterPage = () => <AuthForm register />;
