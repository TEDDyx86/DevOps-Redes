import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

function loadCredentials(): { username: string; password: string } {
  const envUser = process.env.ADMIN_USERNAME;
  const envPass = process.env.ADMIN_PASSWORD;
  if (envUser && envPass) {
    return { username: envUser, password: envPass };
  }

  const envPath = path.resolve(process.cwd(), "..", ".env");
  if (!fs.existsSync(envPath)) {
    throw new Error(
      "Arquivo .env não encontrado na raiz do projeto. Execute python scripts/configure.py primeiro.",
    );
  }
  const values: Record<string, string> = {};
  for (const line of fs.readFileSync(envPath, "utf-8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const raw = trimmed.slice(eq + 1).trim();
    values[key] = raw.replace(/^(['"])(.*)\1$/, "$2");
  }
  if (!values.ADMIN_PASSWORD) {
    throw new Error("ADMIN_PASSWORD ausente no arquivo .env.");
  }
  return {
    username: values.ADMIN_USERNAME || "admin",
    password: values.ADMIN_PASSWORD,
  };
}

const SIDEBAR_AREAS: {
  id: string;
  heading: string;
  markers: string[];
}[] = [
  {
    id: "overview",
    heading: "Visão geral",
    markers: ["Aplicação HTTP", "PostgreSQL", "DNS CoreDNS", "SMTP Local"],
  },
  {
    id: "service",
    heading: "Aplicação HTTP",
    markers: [
      "Requisições por segundo",
      "Respostas 4xx e 5xx",
      "Códigos de erro (janela)",
      "Conexões ativas",
    ],
  },
  {
    id: "security",
    heading: "Segurança",
    markers: ["Vulnerabilidades conhecidas"],
  },
  {
    id: "incidents",
    heading: "Incidentes",
    markers: ["Histórico de incidentes"],
  },
  {
    id: "attacks",
    heading: "Ataques",
    markers: ["Monitoramento ao vivo", "Catálogo de ataques", "Fila de execução"],
  },
];

const SERVICE_SUBTABS: { label: string; heading: string; markers: string[] }[] = [
  {
    label: "PostgreSQL",
    heading: "PostgreSQL",
    markers: ["Disponibilidade SQL", "Conexões abertas", "Consultas lentas"],
  },
  {
    label: "DNS",
    heading: "DNS",
    markers: ["Disponibilidade DNS", "Tempo de resolução", "Registro verificado"],
  },
  {
    label: "SMTP",
    heading: "SMTP",
    markers: ["Mensagens na fila", "Entregues do total aceito", "O caminho da mensagem"],
  },
  {
    label: "Recursos (CPU/RAM/I/O)",
    heading: "Recursos",
    markers: ["Consumo por serviço", "CPU utilizada"],
  },
];

test("login pela interface e navegação completa nas 5 áreas e sub-abas do painel", async ({
  page,
}) => {
  const { username, password } = loadCredentials();
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => {
    consoleErrors.push(err.message);
  });

  await page.goto("/");

  // Landing pública -> tela de login
  const enterButton = page.getByRole("button", { name: /Entrar|Acessar o painel/i }).first();
  if (await enterButton.isVisible()) {
    await enterButton.click();
  }

  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /^Entrar$/ }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Visão geral" })).toBeVisible();
  await expect(page.locator(".health-strip")).toBeVisible();

  for (const item of SIDEBAR_AREAS) {
    await page.locator(`nav[aria-label="Navegação principal"] a[href="#${item.id}"]`).click();
    await expect(
      page.getByRole("heading", { level: 1, name: item.heading }),
    ).toBeVisible();
    for (const marker of item.markers) {
      await expect(page.locator("main#main")).toContainText(marker);
    }
  }

  // Sub-abas de Serviços (PostgreSQL, DNS, SMTP, Recursos)
  await page.locator('nav[aria-label="Navegação principal"] a[href="#service"]').click();
  for (const sub of SERVICE_SUBTABS) {
    await page.getByRole("button", { name: sub.label, exact: true }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: sub.heading }),
    ).toBeVisible();
    for (const marker of sub.markers) {
      await expect(page.locator("main#main")).toContainText(marker);
    }
  }

  // Sub-abas de Segurança
  await page.locator('nav[aria-label="Navegação principal"] a[href="#security"]').click();
  for (const [label, marker] of [
    ["Integridade", "Integridade das configurações"],
    ["Tráfego", "Tráfego dos serviços"],
    ["Autenticação", "Acesso ao painel"],
  ] as const) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.locator("main#main")).toContainText(marker);
  }

  // Sub-aba Laboratório manual dentro de Ataques & Lab
  await page.locator('nav[aria-label="Navegação principal"] a[href="#attacks"]').click();
  await page.getByRole("button", { name: "Laboratório manual", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Laboratório" })).toBeVisible();
  await expect(page.locator("main#main")).toContainText("Controle do serviço HTTP");

  // Verifica responsividade mobile sem transbordamento horizontal
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#overview");
  await expect(page.getByRole("heading", { level: 1, name: "Visão geral" })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
  expect(consoleErrors).toEqual([]);
});
