const PHASES = ["agendado", "preparando", "executando", "verificando", "concluido"];
const FINAL_ICONS = { concluido: "✅", interrompido: "🛑", falhou: "❌" };

async function jfetch(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function renderCatalog(attacks) {
  const grid = document.getElementById("ataques");
  grid.innerHTML = "";
  for (const attack of attacks) {
    const card = document.createElement("article");
    card.className = "card";
    const inputs = (attack.params || []).map((spec) => {
      if (spec.type === "int") {
        return `<label>${spec.name} <input type="number" data-param="${spec.name}" value="${spec.default}" min="${spec.min}" max="${spec.max}"></label>`;
      }
      const options = (spec.options || []).map((option) => `<option ${option === spec.default ? "selected" : ""}>${option}</option>`).join("");
      return `<label>${spec.name} <select data-param="${spec.name}">${options}</select></label>`;
    }).join("");
    card.innerHTML = `<h3>${attack.name}</h3><p class="target">${attack.target}</p><p>${attack.description}</p>
      <p class="alerts">Alertas esperados: ${attack.expected_alerts.join(", ") || "depende do alvo"}</p>
      <div class="params">${inputs}</div>
      <button data-start="${attack.id}">Iniciar</button>`;
    grid.appendChild(card);
  }
}

function phases(entry) {
  const current = PHASES.indexOf(entry.status);
  return PHASES.map((phase, index) => `<span class="phase ${index <= current ? "done" : ""}">${phase}</span>`).join(" → ");
}

function verification(entry) {
  if (!entry || !entry.verification) return "";
  const result = entry.verification;
  if (!result.available) return `<p class="warn">⚠️ Verificação indisponível (Prometheus fora do ar?)</p>`;
  if (result.fired.length) return `<p class="ok">✅ Alerta disparou: ${result.fired.join(", ")}</p>`;
  return `<p class="warn">⚠️ Não disparou (verificar): ${result.missing.join(", ")}</p>`;
}

function counters(entry) {
  const items = Object.entries(entry.counters || {});
  return items.length ? `<p class="counters">${items.map(([key, value]) => `${key}: ${value}`).join(" · ")}</p>` : "";
}

function entryView(entry) {
  const aberto = !["concluido", "falhou", "interrompido"].includes(entry.status);
  return `<article class="entry status-${entry.status}">
    <h4>${entry.attack} <span class="status">${entry.status}${FINAL_ICONS[entry.status] ? " " + FINAL_ICONS[entry.status] : ""}</span></h4>
    <p class="phases">${phases(entry)}</p>
    ${counters(entry)}
    ${verification(entry)}
    ${aberto ? `<button data-cancel="${entry.entry_id}">Interromper</button>` : ""}
  </article>`;
}

async function refresh() {
  try {
    const snapshot = await jfetch("/api/queue");
    document.getElementById("atual").innerHTML = snapshot.current
      ? entryView(snapshot.current) : `<p class="idle">Nenhum ataque em execução.</p>`;
    document.getElementById("fila").innerHTML = snapshot.queue.length
      ? `<h3>Fila</h3>${snapshot.queue.map(entryView).join("")}` : "";
    document.getElementById("historico").innerHTML = snapshot.history.length
      ? `<h3>Histórico</h3>${snapshot.history.slice().reverse().map(entryView).join("")}` : "";
  } catch (error) { /* servidor fora do ar; próxima tentativa em 2 s */ }
}

document.addEventListener("click", async (event) => {
  if (event.target.dataset && event.target.dataset.cancel) {
    await jfetch(`/api/queue/${event.target.dataset.cancel}/cancel`, { method: "POST" }).catch(() => {});
    refresh();
  }
  if (event.target.dataset && event.target.dataset.start) {
    const id = event.target.dataset.start;
    const card = event.target.closest(".card");
    const params = {};
    card.querySelectorAll("[data-param]").forEach((input) => {
      params[input.dataset.param] = input.tagName === "SELECT" ? input.value : Number(input.value);
    });
    try {
      await jfetch(`/api/attacks/${id}/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ params }) });
    } catch (error) { alert("Falha ao iniciar: " + error.message); }
    refresh();
  }
});

const logBox = document.getElementById("log-box");
logBox.textContent = "";
const source = new EventSource("/api/events");
source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "log") {
    logBox.textContent += `[${new Date().toLocaleTimeString("pt-BR")}] ${data.message}\n`;
    logBox.scrollTop = logBox.scrollHeight;
  }
};

jfetch("/api/attacks").then((data) => renderCatalog(data.attacks)).catch(() => {});
refresh();
setInterval(refresh, 2000);
