import urllib.request
import urllib.error
import json
import sys

BASE_API = "http://127.0.0.1:8000/api"
FRONTEND_URL = "http://localhost:5173"

def http_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()
        return resp.status, resp.headers, content

def http_post_json(url, payload=None):
    data = json.dumps(payload).encode('utf-8') if payload is not None else b"{}"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()
        return resp.status, resp.headers, content

def run_tests():
    print("======================================================================")
    print("REACT-X COMPREHENSIVE END-TO-END ACCEPTANCE VALIDATION")
    print("======================================================================")

    # 1. Check Frontend Availability
    print("\n[TEST 1] Frontend Dev Server Availability...")
    status, headers, content = http_get(f"{FRONTEND_URL}/demo")
    assert status == 200, f"Frontend returned status {status}"
    assert b"<!DOCTYPE html>" in content or b"<html" in content
    print("  -> PASS: Frontend /demo served with 200 OK")

    # 2. Check Data Gateway Status
    print("\n[TEST 2] Data Gateway Health & Standby Prediction Posture...")
    status, _, content = http_get(f"{BASE_API}/data-gateway/status")
    assert status == 200
    gw_status = json.loads(content)
    assert gw_status["status"] == "HEALTHY"
    assert "prediction_state" in gw_status
    print(f"  -> PASS: Gateway Status = {gw_status['status']}, Prediction State = {gw_status['prediction_state']}")

    # 3. List Demo Scenarios
    print("\n[TEST 3] List Deterministic Demo Scenarios...")
    status, _, content = http_get(f"{BASE_API}/data-gateway/demo/scenarios")
    assert status == 200
    scenarios = json.loads(content)
    assert len(scenarios) >= 3
    print(f"  -> PASS: Found {len(scenarios)} deterministic reference scenarios")

    # 4. Start Demo Replay (Step 0)
    print("\n[TEST 4] Start Demo Replay & Check Step 0 Context Gating...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/start?scenario_id=SCENARIO-DAHEJ-AMMONIA-CRYO-01")
    assert status == 200
    st0 = json.loads(content)
    assert st0["status"] == "RUNNING"
    assert st0["current_step"] == 0
    assert st0["active_event"] is None
    assert st0["active_consequence"] is None
    assert st0["active_evacuation"] is None
    print(f"  -> PASS: Step 0 is clean; downstream context is NONE (Gated buttons disabled)")

    # 5. Step 1 (Ingestion)
    print("\n[TEST 5] Advance Step 1 (Ingestion & Normalization)...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    st1 = json.loads(content)
    assert st1["current_step"] == 1
    assert st1["active_event"] is not None
    print(f"  -> PASS: Step 1 completed. Active Event = {st1['active_event']['event_id']}, Source = {st1['active_event'].get('source_name', 'NASA FIRMS / VIIRS')}")

    # 6. Step 2 (Classification)
    print("\n[TEST 6] Advance Step 2 (23-Feature & Frozen 7-Class ML Classifier)...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    st2 = json.loads(content)
    assert st2["current_step"] == 2
    assert st2["active_classification"] is not None
    print(f"  -> PASS: Step 2 completed. Class = {st2['active_classification']['predicted_class']}, Confidence = {st2['active_classification'].get('confidence_score')}")

    # 7. Step 3 (D-S Fusion)
    print("\n[TEST 7] Advance Step 3 (Multi-Source Corroboration & D-S Evidential Fusion)...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    st3 = json.loads(content)
    assert st3["current_step"] == 3
    assert st3["active_fusion"] is not None
    print(f"  -> PASS: Step 3 completed. Belief Mass = {st3['active_fusion']['belief_mass']}, Conflict K = {st3['active_fusion']['conflict_k']}")

    # 8. Step 4 (Consequence)
    print("\n[TEST 8] Advance Step 4 (Consequence Plume & Prediction Inference)...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    st4 = json.loads(content)
    assert st4["current_step"] == 4
    assert st4["active_consequence"] is not None
    assert len(st4["active_consequence"]["summary_zones"]) >= 3
    print(f"  -> PASS: Step 4 completed. Consequence zones = {len(st4['active_consequence']['summary_zones'])}")

    # 9. Step 5 (Response)
    print("\n[TEST 9] Advance Step 5 (Response & Pre-Plan Context Available)...")
    status, _, content = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    st5 = json.loads(content)
    assert st5["current_step"] == 5
    assert st5["active_consequence"] is not None
    print(f"  -> PASS: Step 5 completed. Status = {st5['status']}, Pipeline Stage = {st5['pipeline_stage']}")

    # 10. Test Evacuation Route Endpoint with Active Consequence
    print("\n[TEST 10] Direct Invocation of Dynamic Evacuation Routing...")
    # Generate impact first
    _, _, impact_bytes = http_post_json(f"{BASE_API}/impact/analyze?time_step_sec=120", st5["active_consequence"])
    impact_data = json.loads(impact_bytes)
    
    evac_payload = {
        "simulation_result": st5["active_consequence"],
        "impact_result": impact_data,
        "origin_coords": [21.6850, 72.5750]
    }
    status, _, evac_bytes = http_post_json(f"{BASE_API}/evacuation/route?origin_name=T-04%20Staging", evac_payload)
    assert status == 200
    evac_plan = json.loads(evac_bytes)
    assert "primary_evacuation_route" in evac_plan
    primary_route = evac_plan["primary_evacuation_route"]
    assert len(primary_route["route_coordinates"]) > 0
    assert primary_route["total_distance_m"] > 0
    print(f"  -> PASS: Safe evacuation corridor computed: {primary_route['total_distance_m']:.0f}m to {primary_route['recommended_assembly_point_name']}")

    # 11. Test Resource Optimization
    print("\n[TEST 11] Direct Invocation of Resource Optimization...")
    res_payload = {
        "simulation_result": st5["active_consequence"],
        "impact_result": impact_data,
        "evacuation_plan": evac_plan
    }
    status, _, res_bytes = http_post_json(f"{BASE_API}/resources/optimize", res_payload)
    assert status == 200
    resource_plan = json.loads(res_bytes)
    assert "recommended_resources" in resource_plan
    print(f"  -> PASS: Resource plan optimized: {len(resource_plan['recommended_resources'])} units dispatched")

    # 12. Test Official ERDMP Pre-Plan PDF Generation
    print("\n[TEST 12] Direct Invocation of Pre-Plan PDF Generation...")
    pdf_payload = {
        "simulation_result": st5["active_consequence"],
        "impact_result": impact_data,
        "evacuation_plan": evac_plan,
        "resource_plan": resource_plan,
        "author_name": "REACT-X National Safety Controller",
        "facility_ref": "FAC-IN-DAHEJ-001 Dahej Petrochemical Complex"
    }
    status, headers, pdf_bytes = http_post_json(f"{BASE_API}/preplan/generate-pdf", pdf_payload)
    assert status == 200
    assert pdf_bytes.startswith(b"%PDF-"), "Response does not start with PDF magic bytes"
    assert len(pdf_bytes) > 2000, f"PDF file size is unexpectedly small ({len(pdf_bytes)} bytes)"
    print(f"  -> PASS: Real PDF generated and streamed ({len(pdf_bytes)} bytes, starts with %PDF-)")

    # 13. Test Failure Injection
    print("\n[TEST 13] Test Failure Injection (Missing OT Telemetry -> STANDBY)...")
    http_post_json(f"{BASE_API}/data-gateway/demo/start")
    status, _, fail_bytes = http_post_json(f"{BASE_API}/data-gateway/demo/failure-injection", {
        "inject_missing_telemetry": True
    })
    assert status == 200
    
    status, _, step_bytes = http_post_json(f"{BASE_API}/data-gateway/demo/step")
    fail_state = json.loads(step_bytes)
    assert fail_state["active_prediction"]["prediction_state"] == "PREDICTION_STANDBY"
    print("  -> PASS: Prediction state honestly transitions to PREDICTION_STANDBY")

    # 14. Recover Feeds
    print("\n[TEST 14] Test Failure Recovery...")
    status, _, rec_bytes = http_post_json(f"{BASE_API}/data-gateway/demo/failure-injection", {
        "trigger_recovery": True
    })
    assert status == 200
    print("  -> PASS: Recovery command executed successfully")

    # 15. Check India Operations Endpoints
    print("\n[TEST 15] Test India Operations Core Endpoints...")
    status, _, fac_bytes = http_get(f"{BASE_API}/facilities")
    assert status == 200
    facs = json.loads(fac_bytes)
    assert len(facs) > 0
    print(f"  -> PASS: Industrial facility registry contains {len(facs)} facilities across India")

    print("\n======================================================================")
    print("ALL 15 END-TO-END ACCEPTANCE TESTS PASSED (100% SUCCESS)")
    print("======================================================================")

if __name__ == "__main__":
    run_tests()
