# Industrial Facility Telemetry Integration Guide

**System:** REACT-X High-Frequency Telemetry Gateway  
**Document Version:** 1.0.0  
**Target Audience:** Plant Automation Engineers, OT/IT Integration Specialists, Process Safety Managers  

---

## 1. Overview & Integration Philosophy

This guide outlines how an industrial petrochemical plant, refinery, or manufacturing facility can securely expose read-only process and safety measurements to REACT-X **without granting REACT-X control, write, or actuation access to plant equipment**.

---

## 2. Supported Ingestion Protocols

REACT-X provides three standard edge ingestion methods:

### Option A: Read-Only OPC UA Client Ingestion
1. **Plant Setup:**
   - Configure an OPC UA Server (e.g. Kepware KEPServerEX, Siemens SIMATIC NET, PTC ThingWorx Kepware Edge).
   - Create a dedicated read-only User Account with `Read` and `Subscribe` permissions only (disable `Write`, `Call Method`, and `Admin`).
   - Enable TLS certificate validation (`Basic256Sha256` or `Aes128_Sha256_RsaOaep`).
2. **REACT-X Configuration:**
   Set environment variables:
   ```bash
   OPCUA_ENDPOINT_URL="opc.tcp://edge-gateway.plant.local:4840/REACTX/OPCUAServer"
   OPCUA_SECURITY_POLICY="Basic256Sha256_SignAndEncrypt"
   OPCUA_USERNAME="reactx_readonly_consumer"
   OPCUA_PASSWORD="<SecureVaultSecret>"
   ```

### Option B: Read-Only MQTT / Sparkplug B Subscriber Ingestion
1. **Plant Setup:**
   - Plant Edge Gateway publishes sensor metrics to an industrial MQTT broker (e.g. HiveMQ, EMQX, Mosquitto).
   - Topic convention (Sparkplug B format):
     `spBv1.0/<FacilityId>/DDATA/<PlantArea>/<AssetId>/<SensorName>`
     or standard JSON payload:
     `plant/<facility_id>/<asset_id>/<sensor_type>`
   - Restrict ACLs on the broker so the `reactx_subscriber` identity has `SUBSCRIBE` permissions only and CANNOT `PUBLISH` to control topics (`DCMD`, `NCMD`).
2. **REACT-X Configuration:**
   Set environment variables:
   ```bash
   MQTT_BROKER_HOST="mqtt.plant.local"
   MQTT_BROKER_PORT=8883
   MQTT_USE_TLS=true
   MQTT_USERNAME="reactx_subscriber"
   MQTT_PASSWORD="<SecureVaultSecret>"
   ```

### Option C: Push-Based REST Webhook Ingestion
Plant edge gateway posts batches of readings directly to the REACT-X push endpoint:
- **Endpoint:** `POST /api/telemetry/ingest`
- **Payload:** List of `FacilityTelemetryObservation` JSON objects.

---

## 3. Sensor Tag Hierarchy & Schema

Sensors must be mapped to the hierarchical taxonomy:
```
FACILITY (e.g. FAC-IN-DAHEJ-001)
  └── PLANT / AREA (e.g. Sector D - Cryogenic Yard)
       └── UNIT (e.g. UNIT-NH3-01)
            └── ASSET (e.g. T-04 Ammonia Cryogenic Tank)
                 └── SENSOR / TAG (e.g. SENS-T04-TEMP-01)
```

### Supported Sensor Types & Normalized Engineering Units:
- **Temperature:** `°C` (Transmitters in `K` or `°F` are normalized)
- **Pressure:** `bar` (Transmitters in `kPa` or `psi` are normalized)
- **Gas Concentration:** `ppm`
- **Flow Rate:** `m³/h` (Transmitters in `L/min` are normalized)
- **Vibration:** `mm/s` (RMS Velocity)
- **Thermal Camera Summary:** `score` (0.0 to 100.0)
- **Process State:** `state` (0 to 10 integer states)

---

## 4. Hardware Connectivity Status

> [!NOTE]
> **CURRENT DEPLOYMENT STATUS:**  
> **REAL INDUSTRIAL TELEMETRY NOT YET CONNECTED; INTERFACE READY.**  
> 
> The system operates in **High-Fidelity Simulated Industrial Telemetry Mode** by default. When physical edge gateways are provisioned, credentials and endpoints are injected via environment variables without requiring code changes.
