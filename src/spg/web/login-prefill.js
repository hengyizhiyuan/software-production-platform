/* Single-owner login convenience, shared by product and Admin forms. */
window.WattLogin = {
  async prefill(form) {
    const input = form?.elements.namedItem('token');
    if (!input || input.value) return;
    try {
      const response = await fetch('/auth/login-prefill', {
        credentials: 'same-origin', cache: 'no-store',
      });
      if (!response.ok) return;
      const {token} = await response.json();
      // A delayed response must not replace a user's input or a newer form.
      if (input.isConnected && !input.value && typeof token === 'string') input.value = token;
    } catch (_) {
      // Manual login remains available when prefill is unavailable.
    }
  },
};
