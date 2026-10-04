"""Deterministic synthetic Phase 3 safety-contract release gate."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Mapping
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app import aki_explanations, auth
from app.aki_features import FEATURE_SCHEMA, FRESHNESS_POLICY, LABEL_VERSION, build_prediction_snapshot
from app.aki_model import package_versions
from app.clinical_rules import calculate_creatinine_rule
from app.patients import ClinicalContext, PatientDetail, PatientSummary
from app.prediction_service import VerifiedPredictionEngine, validate_aki_prediction_result
from app.synthetic_data import EhrEvent, IotObservation
CUTOFF = datetime(2026, 1, 15, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]
def canonical(value: object) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
def digest(value: object) -> str: return hashlib.sha256(canonical(value).encode()).hexdigest()
def event(hours: float, value: object, **data: object) -> EhrEvent:
    return EhrEvent(event_id=f"eval-ehr-{hours}",patient_id="tbp-contract",event_type="laboratory",event_time=CUTOFF-timedelta(hours=hours),data={"test_name":"creatinine","value":value,"unit":"mg/dL",**data},synthetic=True,generator_version="reference-v1",seed=1,source="twinbean-synthetic-ehr")
def observation(hours: float=0, **data: object) -> IotObservation:
    return IotObservation(observation_id=f"eval-iot-{hours}",patient_id="tbp-contract",measurement_type="blood_pressure",observed_at=CUTOFF-timedelta(hours=hours),data={"systolic":130,"diastolic":80,"unit":"mmHg",**data},synthetic=True,generator_version="reference-v1",seed=1,source="twinbean-simulated-iot")
def context(events: list[EhrEvent]|None=None, observations: list[IotObservation]|None=None) -> ClinicalContext:
    return ClinicalContext(cohort_id="cohort-contract",manifest_checksum="a"*64,generator_version="reference-v1",seed=1,patient=PatientDetail(patient=PatientSummary(patient_id="tbp-contract",display_name="Synthetic Contract Patient",age=61,ckd_stage="G3b"),ehr_history=events or [event(20,1.1),event(0,1.2)],iot_observations=observations or [observation()]))
def rule_events(items: list[Mapping[str,object]]) -> list[EhrEvent]:
    result=[]
    for item in items:
        when=CUTOFF-timedelta(hours=float(item["hours_before_cutoff"]))
        if item.get("timestamp_kind")=="naive": when=when.replace(tzinfo=None)
        result.append(EhrEvent(event_id=str(item["id"]),patient_id="tbp-reference-patient",event_type="laboratory",event_time=when,data={"test_name":"creatinine","value":item["value"],"unit":item["unit"]},synthetic=True,generator_version="reference-v1",seed=1,source="twinbean-synthetic-ehr"))
    return result
def run_rule(item: dict, legacy: dict) -> dict:
    source=legacy[item["reference_scenario"]]; result=calculate_creatinine_rule(rule_events(source["events"]),CUTOFF)
    actual={"status":result.status,"criteria_evaluated":result.criteria_evaluated,"criteria_met":result.criteria_met,"evidence_event_ids":[e.event_id for e in result.evidence]}
    expected={"status":source["expected_status"],"criteria_evaluated":source["expected_criteria_evaluated"],"criteria_met":source["expected_criteria_met"],"evidence_event_ids":source["expected_evidence_event_ids"]}
    return {"actual":actual,"passed":actual==expected}
def snapshot_for(strategy: str):
    current=context(); cutoff=CUTOFF
    if strategy=="invalid_cutoff": cutoff=cutoff.replace(tzinfo=None)
    elif strategy=="missing_history": current=context([event(0,1.2)])
    elif strategy=="missing_comparator": current=context([event(49,1.1),event(0,1.2)])
    elif strategy=="stale_ehr": current=context([event(26,1.1),event(25,1.2)])
    elif strategy=="stale_iot": current=context(observations=[observation(25)])
    elif strategy=="future_observation": current=context([event(-1,1.3),event(0,1.2),event(20,1.1)])
    elif strategy=="forbidden_field": current=context([event(20,1.1),event(0,1.2,scenario="leak")])
    elif strategy=="invalid_iot_unit": current=context(observations=[observation(unit="kPa")])
    return build_prediction_snapshot(current,cutoff)
def run_forecast(item: dict) -> dict:
    first=VerifiedPredictionEngine().predict(context(),CUTOFF); second=VerifiedPredictionEngine().predict(context(),CUTOFF) if item.get("strategy")=="reproducible" else first
    actual={"status":first.status}
    passed=actual==item["expected"] and bool(getattr(first,"attributions",()))
    if item.get("strategy")=="reproducible": passed=passed and first.probability==second.probability
    return {"actual":actual,"passed":passed}
def run_unavailable(item: dict) -> dict:
    strategy=item["strategy"]
    if strategy=="artifact_failure":
        engine=VerifiedPredictionEngine(); engine._artifact_dir=ROOT/"not-a-release"; result=engine.predict(context(),CUTOFF)
    elif strategy=="shap_failure":
        original=aki_explanations.shap.TreeExplainer
        class Broken:
            def __init__(self,*args,**kwargs): raise RuntimeError("synthetic SHAP failure")
        aki_explanations.shap.TreeExplainer=Broken
        try: result=VerifiedPredictionEngine().predict(context(),CUTOFF)
        finally: aki_explanations.shap.TreeExplainer=original
    else: result=snapshot_for(strategy)
    actual={"status":result.status,"reason":getattr(result,"reason",None) or getattr(result,"reasons",[None])[0]}
    return {"actual":actual,"passed":actual==item["expected"]}
def direct_rubrics(category: str, scenario: Mapping[str, object]) -> list[str]:
    """Return only rubrics directly exercised by this evaluator runner."""
    if category == "valid_forecast":
        return ["D-09"] if scenario.get("strategy") == "reproducible" else []
    if category == "unavailable_or_adversarial" and scenario.get("strategy") == "artifact_failure":
        return []
    if category == "end_to_end_integrity" and scenario.get("strategy") == "separation":
        return []
    return list(scenario["rubrics"])

def run_integrity(item: dict) -> dict:
    strategy=item["strategy"]
    if strategy=="authorization":
        original=auth.verify_firebase_token; auth.verify_firebase_token=lambda _: {"role":"researcher"}
        try:
            try: auth.require_doctor(HTTPAuthorizationCredentials(scheme="Bearer",credentials="synthetic")); status="accepted"
            except HTTPException as error: status="rejected" if error.status_code==403 else "wrong_status"
        finally: auth.verify_firebase_token=original
    elif strategy=="atomicity":
        status="preserved" if subprocess.run([sys.executable,"-m","pytest","backend/tests/test_patients.py::test_failed_clinical_result_transaction_leaves_all_existing_documents_unchanged","-q"],cwd=ROOT,capture_output=True).returncode==0 else "failed"
    else:
        try: validate_aki_prediction_result({"status":"unavailable","outcome":"new_aki_within_24h","prediction_cutoff":CUTOFF,"generated_at":CUTOFF,"reasons":["missing"],"evidence":[]}); status="accepted"
        except Exception: status="rejected"
    return {"actual":{"status":status},"passed":status==item["expected"]["status"]}
def revision() -> str:
    try: return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    except Exception: return "unavailable"
def evaluate_contract(reference: Path, output: Path, *, fail_on_rubric: bool=False) -> dict:
    data=json.loads(reference.read_text(encoding="utf-8")); categories=data["scenario_categories"]; legacy={x["name"]:x for x in data["scenarios"]}; results=[]
    runners={"rule":lambda x:run_rule(x,legacy),"valid_forecast":run_forecast,"unavailable_or_adversarial":run_unavailable,"end_to_end_integrity":run_integrity}
    for category,scenarios in categories.items():
        for scenario in scenarios: results.append({"name":scenario["name"],"category":category,"rubrics":direct_rubrics(category,scenario),**runners[category](scenario)})
    failures=[{"name":x["name"],"actual":x["actual"]} for x in results if not x["passed"]]; rubrics={f"D-{n:02d}":{"cases":0,"passed":0} for n in range(1,17)}
    for result in results:
        for rubric in result["rubrics"]: rubrics[rubric]["cases"]+=1; rubrics[rubric]["passed"]+=int(result["passed"])
    artifact=json.loads((ROOT/"backend/model_artifacts/aki-24h-2026.10.04/manifest.json").read_text(encoding="utf-8"))
    manifest={"format_version":1,"command":"python -m scripts.evaluate_phase3_contract","generated_at_utc":datetime.now(UTC).isoformat(),"code_revision":revision(),"reference_sha256":digest(data),"synthetic_research_only":True,"clinical_validated":False,"limitations":["Synthetic safety-contract scenarios only; not a held-out performance, calibration, prevalence, or clinical-validation report."],"artifact":{"model_version":artifact["model_version"],"members":artifact["members"],"schema":artifact["feature_schema"],"package_versions":package_versions()},"cutoff_version":"utc-cutoff-v1","label_version":LABEL_VERSION,"feature_schema_version":FEATURE_SCHEMA.version,"freshness_policy_version":FRESHNESS_POLICY.version,"scenario_counts":{**{k:len(v) for k,v in categories.items()},"total":len(results)},"rubric_counts":rubrics,"not_evaluated_rubrics":[name for name, count in rubrics.items() if count["cases"] == 0],"critical_failures":failures,"results":results,"seeds":sorted({x["synthetic_provenance"]["seed"] for v in categories.values() for x in v}),"partition_digests":artifact["partition"]}
    manifest["output_digest"]=digest(manifest); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if fail_on_rubric and failures: raise RuntimeError(f"{len(failures)} critical scenarios failed")
    return manifest
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--reference",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--fail-on-rubric",action="store_true"); args=parser.parse_args()
    try: evaluate_contract(args.reference,args.output,fail_on_rubric=args.fail_on_rubric)
    except Exception as error: print(f"Phase 3 contract evaluation failed: {error}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
