// Same rules as the backend (identity/service.py) so most mistakes are caught before sending a request
export function validateCredentials({ email, password, confirm }, { register = false } = {}) {
  const errors = {};
  if (!email.trim()) errors.email = 'Podaj adres e-mail.';
  else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) errors.email = 'Niepoprawny adres e-mail.';
  if (!password) errors.password = 'Podaj hasło.';
  else if (register) {
    if (password.length < 8) errors.password = 'Hasło musi mieć min. 8 znaków.';
    else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) errors.password = 'Hasło musi zawierać literę i cyfrę.';
    if (confirm !== password) errors.confirm = 'Hasła nie są takie same.';
  }
  return errors;
}
