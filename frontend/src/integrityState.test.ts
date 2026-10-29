import { describe, it, expect } from "vitest";
import { currentFile, approvalCandidates, reviewStillCurrent, type IntegrityFile } from "./integrityState";

const row: IntegrityFile = { id:"http-runtime", name:"HTTP", service:"web-demo", path:"http.json", status:"unapproved", observed_sha256:"a".repeat(64), approved_sha256:null, approved_at:null, approved_by:null, checked_at:100, reason:null };
describe("integridade de configurações", () => {
  it("expira a observação sem apagar a referência aprovada", () => {
    const expired=currentFile({...row, status:"ok", approved_sha256:row.observed_sha256},121);
    expect(expired.status).toBe("unknown");
    expect(expired.observed_sha256).toBeNull();
    expect(expired.approved_sha256).toBe(row.observed_sha256);
  });
  it("a seleção inicial reúne somente arquivos sem referência e legíveis", () => {
    expect(approvalCandidates([row,{...row,id:"dns-zone",status:"changed"},{...row,id:"smtp-runtime",status:"missing",observed_sha256:null}],"pending")).toEqual([row]);
    expect(approvalCandidates([row],"http-runtime")).toEqual([row]);
  });
  it("uma nova observação não substitui o hash em revisão", () => {
    const review=[{file_id:row.id,observed_sha256:row.observed_sha256!}];
    expect(reviewStillCurrent(review,[row])).toBe(true);
    expect(reviewStillCurrent(review,[{...row,observed_sha256:"b".repeat(64)}])).toBe(false);
    expect(reviewStillCurrent(review,[currentFile(row,121)])).toBe(false);
    expect(reviewStillCurrent([], [row])).toBe(false);
  });
});
