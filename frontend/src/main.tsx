import React from "react";
import ReactDOM from "react-dom/client";
import Auth from "./Auth";
import "@fontsource/press-start-2p";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-700.css";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Auth />
  </React.StrictMode>,
);
