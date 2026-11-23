const form = document.querySelector('[data-contact-form]');
const statusMessage = form.querySelector('[data-form-status]');
const submit = form.querySelector('button[type=submit]');

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (submit.disabled || !form.reportValidity()) return;
  submit.disabled = true;
  statusMessage.textContent = 'Invio in corso…';
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: {Accept: 'application/json'}
    });
    if (!response.ok || (await response.json()).success !== true) {
      throw new Error('Richiesta non confermata');
    }
    form.reset();
    statusMessage.textContent = 'Grazie, la tua richiesta è stata inviata.';
  } catch {
    statusMessage.textContent = 'Invio non confermato. Puoi scrivere a amministrazione@studiolava.it.';
  } finally {
    submit.disabled = false;
  }
});

if (new URLSearchParams(location.search).get('contatto') === '1') {
  form.querySelector('#contact-name').focus();
}
