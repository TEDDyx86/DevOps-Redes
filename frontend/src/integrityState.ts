export interface IntegrityFile {
  id:string; name:string; service:string; path:string;
  status:"ok"|"unapproved"|"changed"|"missing"|"unreadable"|"unknown";
  observed_sha256:string|null; approved_sha256:string|null;
  approved_at:number|null; approved_by:string|null; checked_at:number|null; reason:string|null;
}
export interface Approval { file_id:string; observed_sha256:string }
export interface IntegrityOverview {
  enabled:boolean; generated_at:number; files:IntegrityFile[];
  events:{id:number;at:number;file_id:string;kind:string;old_sha256:string|null;new_sha256:string|null;actor:string|null}[];
}
export function currentFile(row:IntegrityFile,now:number):IntegrityFile {
  return row.checked_at!==null && now-row.checked_at<=20 && now-row.checked_at>=-5
    ? row : {...row,status:"unknown",observed_sha256:null};
}
export function approvalCandidates(rows:IntegrityFile[],selection:string) {
  return rows.filter(row => row.observed_sha256!==null && ["ok","changed","unapproved"].includes(row.status) && (selection==="pending" ? row.status==="unapproved" : row.id===selection));
}
export function reviewStillCurrent(review:Approval[],rows:IntegrityFile[]) {
  return review.length>0 && review.every(item => rows.some(row => row.id===item.file_id && row.observed_sha256===item.observed_sha256 && ["ok","changed","unapproved"].includes(row.status)));
}
