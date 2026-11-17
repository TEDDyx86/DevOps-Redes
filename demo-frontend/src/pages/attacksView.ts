const STATUS_LABELS: Record<string, string> = {
  agendado: "Agendado",
  preparando: "Preparando",
  executando: "Executando",
  verificando: "Verificando",
  interrompendo: "Interrompendo",
  concluido: "Concluído",
  interrompido: "Interrompido",
  falhou: "Falhou",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export interface VerificationResult {
  available: boolean;
  fired: string[];
  missing: string[];
}

export function verificationLine(result: VerificationResult | null): string {
  if (result === null) return "Aguardando verificação";
  if (!result.available) return "Verificação indisponível";
  if (result.fired.length > 0) return `Disparou: ${result.fired.join(", ")}`;
  if (result.missing.length > 0) return `Não disparou (verificar): ${result.missing.join(", ")}`;
  return "Sem alertas esperados";
}
