const dialog = document.querySelector('#edit-dialog');
document.querySelector('#open-dialog').addEventListener('click', () => dialog.showModal());
document.querySelector('#cancel').addEventListener('click', () => dialog.close());
async function loadLists() {
  const users = await fetch('/api/users').then(response => response.json());
  document.querySelector('#user-list').textContent = users.map(user => user.name).join(', ');
  const customers = await fetch('/api/customers').then(response => response.json());
  document.querySelector('#customer-list').textContent = customers.map(customer => customer.name).join(', ');
}
loadLists();
