"""Verify immutable Phase 3 synthetic safety-contract manifests."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
REQUIRED={"format_version","command","generated_at_utc","code_revision","reference_sha256","synthetic_research_only","clinical_validated","limitations","artifact","cutoff_version","label_version","feature_schema_version","freshness_policy_version","scenario_counts","rubric_counts","critical_failures","results","seeds","partition_digests","not_evaluated_rubrics","output_digest"}
FORBIDDEN=re.compile(r"(?:tbp-[a-z0-9]|bearer\s+|token|credential|secret|password|auroc|auprc|brier|calibration|event prevalence|ehr-only|clinical threshold|fabricated)",re.I)
def canonical(value: object) -> str: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)
def digest(value: object) -> str: return hashlib.sha256(canonical(value).encode()).hexdigest()
def verify_manifest(path: Path) -> bool:
    payload=json.loads(path.read_text(encoding="utf-8"))
    missing=REQUIRED-set(payload)
    if missing: raise ValueError(f"manifest missing required fields: {sorted(missing)}")
    actual=payload.pop("output_digest")
    if not isinstance(actual,str) or actual!=digest(payload): raise ValueError("manifest output digest mismatch")
    if payload["format_version"]!=1 or payload["synthetic_research_only"] is not True or payload["clinical_validated"] is not False: raise ValueError("manifest research-use declarations are invalid")
    if payload["critical_failures"]: raise ValueError("manifest contains critical failures")
    if payload["scenario_counts"].get("total",0)<24: raise ValueError("manifest reports too few scenarios")
    if set(payload["rubric_counts"])!={f"D-{n:02d}" for n in range(1,17)} or any((item["cases"] and item["cases"]!=item["passed"]) or (not item["cases"] and name not in payload["not_evaluated_rubrics"]) for name,item in payload["rubric_counts"].items()): raise ValueError("manifest has an incomplete, failing, or unmarked rubric")
    if not isinstance(payload["partition_digests"],dict) or any("patient" in str(value).lower() and len(str(value))!=64 for value in payload["partition_digests"].values()): raise ValueError("manifest partition metadata is invalid")
    claim_scan=dict(payload)
    claim_scan["limitations"]=[]
    text=canonical(claim_scan)
    if FORBIDDEN.search(text): raise ValueError("manifest contains sensitive identifiers or unsupported performance/clinical claims")
    return True
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("manifest",type=Path); args=parser.parse_args()
    try: verify_manifest(args.manifest)
    except Exception as error: print(f"Phase 3 manifest verification failed: {error}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())