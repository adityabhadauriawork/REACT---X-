# Optical CCTV & Visual Surveillance Integration Guide

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 13 Vision Foundation)  
**Classification:** Plant CCTV Computer Vision  

---

## 1. Scope & Objective

This document outlines the ingestion, classification, and safety parameters for visible-spectrum (RGB) CCTV camera streams within the REACT-X industrial surveillance framework.

---

## 2. Ingestion Pipeline & Model Taxonomy

Visible spectrum optical feeds are processed by `CCTVAdapter` into structured `CCTVFrameEvidence`:

1. **Aerosol & Smoke Plume Detection:**
   - Evaluates chromatic gray-variance and spatial diffusion boundaries.
   - Outputs: `smoke_confidence` $[0.0 - 1.0]$ and bounding box coordinates.
2. **Combustion & Flame Signature Detection:**
   - Evaluates high-intensity red/orange spectral characteristics.
   - Outputs: `flame_confidence` $[0.0 - 1.0]$ and bounding box coordinates.
3. **Scene Status Classification:**
   - `CLEAR` — Normal operational view.
   - `SMOKE_HAZE` — Atmospheric aerosol haze detected.
   - `FLAME_SIGNATURE` — Active optical flame signature detected.
   - `OBSCURED` — Camera lens occluded, dark, or blotted out.
   - `CAMERA_FAULT` — Frame corruption or transport failure.

---

## 3. Strict Read-Only Boundary

> [!WARNING]
> **MANDATORY SAFETY CONSTRAINT:**  
> REACT-X optical adapters are strictly **READ-ONLY**. The software does not send Pan-Tilt-Zoom (PTZ) commands, modify camera firmware, or alter plant security networks.
