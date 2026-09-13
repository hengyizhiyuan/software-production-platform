import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { installNetworkGuard } from "./networkGuard";
import "./styles.css";

installNetworkGuard();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
