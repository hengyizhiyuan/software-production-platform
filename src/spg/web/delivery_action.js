/* Correlate explicit download clicks. Hints never authorize or confirm receipt. */
(() => {
  'use strict';
  function correlateDeliveryAction(anchor, origin, actionId) {
    const url = new URL(anchor.href, origin);
    if (url.origin !== origin) return false;
    let semantic, surface;
    if (/^\/api\/products\/[^/]+\/code-assets\/export$/.test(url.pathname)) {
      semantic = anchor.dataset.deliverySemantic || (url.searchParams.has('revision') ? 'DOWNLOAD_PRODUCT_SOURCE_REVISION' : 'DOWNLOAD_OFFICIAL_PRODUCT_SOURCE');
      surface = 'PRODUCT_SOURCE_EXPORT';
    } else if (/^\/api\/works\/[^/]+\/deliveries\/[^/]+\/download$/.test(url.pathname)) {
      semantic = 'DOWNLOAD_CURRENT_AUTHORIZED_DELIVERY'; surface = anchor.dataset.deliverySurface || 'WORK_DELIVERY';
    } else if (/^\/api\/works\/[^/]+\/deliveries\/[^/]+\/artifact$/.test(url.pathname)) {
      semantic = 'DOWNLOAD_DELIVERY_ARTIFACT'; surface = 'WORK_DELIVERY';
    } else if (/^\/api\/works\/[^/]+\/candidate-download\//.test(url.pathname)) {
      semantic = 'DOWNLOAD_CANDIDATE_ARTIFACT'; surface = 'WORK_DELIVERY';
    } else return false;
    url.searchParams.set('action_semantic', semantic);
    url.searchParams.set('surface', surface);
    url.searchParams.set('initiating_action_id', typeof actionId === 'function' ? actionId() : actionId);
    if (anchor.dataset.deliveryWork) url.searchParams.set('context_work_id', anchor.dataset.deliveryWork);
    anchor.href = url.href;
    return true;
  }
  function initiatingId() {
    if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    // HTTP dogfood ingress is not a secure context; getRandomValues remains available.
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  document.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[href]');
    if (anchor && !event.defaultPrevented) correlateDeliveryAction(anchor, location.origin, initiatingId);
  }, {capture:true});
  window.WattDeliveryAction = {correlateDeliveryAction};
})();
