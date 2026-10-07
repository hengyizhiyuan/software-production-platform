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
    url.searchParams.set('initiating_action_id', actionId);
    if (anchor.dataset.deliveryWork) url.searchParams.set('context_work_id', anchor.dataset.deliveryWork);
    anchor.href = url.href;
    return true;
  }
  document.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[href]');
    if (anchor && !event.defaultPrevented) correlateDeliveryAction(anchor, location.origin, crypto.randomUUID());
  }, {capture:true});
  window.WattDeliveryAction = {correlateDeliveryAction};
})();
