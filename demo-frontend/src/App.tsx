import { useEffect, useState } from "react";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Panel from "./pages/Panel";

const routes: Record<string, () => React.ReactElement> = {
  "/": Landing,
  "/login": Login,
  "/painel": Panel,
};

export default function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const Page = routes[path] ?? Landing;
  return <Page />;
}
