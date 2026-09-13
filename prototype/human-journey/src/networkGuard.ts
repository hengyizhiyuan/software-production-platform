const blocked = (kind: string, target?: unknown): never => {
  const suffix = target ? `：${String(target)}` : "";
  throw new Error(`[Watt Prototype Guard] 已阻止 ${kind}${suffix}`);
};

export function installNetworkGuard(): void {
  window.fetch = ((input: RequestInfo | URL) =>
    Promise.reject(
      new Error(`[Watt Prototype Guard] 已阻止 fetch：${String(input)}`),
    )) as typeof window.fetch;

  window.WebSocket = class BlockedWebSocket {
    constructor(url: string | URL) {
      blocked("WebSocket", url);
    }
  } as unknown as typeof WebSocket;

  window.EventSource = class BlockedEventSource {
    constructor(url: string | URL) {
      blocked("EventSource", url);
    }
  } as unknown as typeof EventSource;

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const action = new URL(form.action || window.location.href, window.location.href);
    if (action.origin !== window.location.origin) {
      event.preventDefault();
      blocked("外部表单提交", action.href);
    }
  });
}
