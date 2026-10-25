import { useCallback, useEffect, useState } from "react";

// Card 1: call /api/health and show the result.
// The tab bar is a placeholder; cards 7, 14 and 15 fill the tabs in.

const TABS = ["STAT", "DATA", "MAP", "INV"];

async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    const body = await res.json().catch(() => null);
    if (res.ok) return { api: "ok", db: "ok" };
    if (body && body.api === "ok") return { api: "ok", db: body.db ?? "down" };
    return { api: "down", db: "unknown" };
  } catch {
    return { api: "down", db: "unknown" };
  }
}

function statusMessage(health) {
  if (health === null) return "CHECKING SYSTEMS...";
  if (health.api !== "ok") {
    return "API OFFLINE. Start it with docker compose up, then try again.";
  }
  if (health.db !== "ok") {
    return "DATABASE OFFLINE. The API is up but cannot reach Postgres. Check the db container.";
  }
  return "ALL SYSTEMS ONLINE.";
}

export default function App() {
  const [health, setHealth] = useState(null);

  const check = useCallback(async () => {
    setHealth(null);
    setHealth(await fetchHealth());
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  const allOk = health && health.api === "ok" && health.db === "ok";

  return (
    <div className="screen">
      <header className="screen-header">
        <h1>NEW VEGAS DIALOGUE EXPLORER</h1>
      </header>

      <nav className="tabs" aria-label="Sections">
        {TABS.map((tab) => (
          <span key={tab} className="tab" aria-disabled="true">
            {tab}
          </span>
        ))}
      </nav>

      <main className="screen-body">
        <h2>SYSTEM STATUS</h2>
        <dl className="status-list">
          <div>
            <dt>API</dt>
            <dd>{health ? health.api.toUpperCase() : "..."}</dd>
          </div>
          <div>
            <dt>DATABASE</dt>
            <dd>{health ? health.db.toUpperCase() : "..."}</dd>
          </div>
        </dl>
        <p role="status" className={allOk ? "message" : "message message-warn"}>
          {statusMessage(health)}
        </p>
        <button type="button" onClick={check} disabled={health === null}>
          CHECK AGAIN
        </button>
      </main>

      <footer className="screen-footer">SEARCH COMING IN CARD 6</footer>
    </div>
  );
}
