import os
import io
import math
from datetime import datetime
from typing import Dict, Any, Optional, List

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas

from app.schemas.hazard import HazardSimulationResult
from app.schemas.impact import ImpactAnalysisResult
from app.schemas.evacuation import EvacuationPlanResponse
from app.schemas.resource import ResourceOptimizationPlan
from app.models.authorization import AuthorizationRecordModel
from app.services.weather.weather_service import weather_service

# Configurable Operational Thresholds
LONG_EGRESS_THRESHOLD_MIN = 30.0

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic 'Page X of Y' numbering and running header/footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.incident_id = "INCIDENT-ACTIVE"
        self.doc_version = "v0.1"
        self.doc_status = "PENDING_HUMAN_AUTHORIZATION"

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Running Top Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 808, f"SIH26162 • INDUSTRIAL EMERGENCY PRE-PLAN • {self.doc_version}")
            self.drawRightString(559, 808, f"INCIDENT: {self.incident_id} [{self.doc_status}]")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(36, 802, 559, 802)

        # Running Bottom Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(36, 36, 559, 36)
        
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#b91c1c"))
        self.drawString(36, 25, "PROTOTYPE DECISION SUPPORT — NON-CERTIFIED • REQUIRES COMPETENT AUTHORITY / ERDMP VALIDATION")
        
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawRightString(559, 25, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class PrePlanService:
    def _render_hazard_dispersion_map(
        self,
        simulation_result: HazardSimulationResult,
        site_data: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        """Render high-resolution Atmospheric Dispersion Plume Map with explicit FROM and TOWARD annotations."""
        fig, ax = plt.subplots(figsize=(6.5, 2.3), dpi=200)
        ax.set_facecolor("#090d16")
        fig.patch.set_facecolor("#090d16")

        src_lat, src_lon = simulation_result.source_coordinates
        wind_deg = simulation_result.wind_direction_deg
        travel_deg = (wind_deg + 180.0) % 360.0
        wind_card = simulation_result.wind_direction_cardinal
        plume_card = weather_service.deg_to_cardinal(travel_deg)
        theta_rad = math.radians(90.0 - travel_deg)

        # Plot threat zones
        for z in reversed(simulation_result.summary_zones):
            d_reach = z.max_downwind_distance_m
            w_cross = z.max_crosswind_width_m
            c = z.color or ("#ef4444" if "Red" in z.name else ("#f97316" if "Orange" in z.name else "#eab308"))
            
            cx = (d_reach * 0.45) * math.cos(theta_rad)
            cy = (d_reach * 0.45) * math.sin(theta_rad)
            
            ellipse = patches.Ellipse(
                (cx, cy),
                width=d_reach * 0.95,
                height=max(40.0, w_cross),
                angle=(90.0 - travel_deg),
                color=c,
                alpha=0.35,
                linewidth=1.2
            )
            ax.add_patch(ellipse)

        # Source Asset Marker
        ax.scatter([0], [0], color="#38bdf8", s=80, zorder=10, edgecolors="white", linewidths=1.5)
        ax.text(0, -32, f"{simulation_result.source_asset_id} ({simulation_result.chemical_name.split('(')[0].strip()})", color="white", fontsize=7.5, fontweight="bold", ha="center", va="top")

        # Explicit Wind Vector & Plume Propagation Indicator
        wind_arrow_len = 200.0
        ax.annotate(
            "",
            xy=(wind_arrow_len * math.cos(theta_rad), wind_arrow_len * math.sin(theta_rad)),
            xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2, mutation_scale=12)
        )
        ax.text(
            wind_arrow_len * 0.55 * math.cos(theta_rad) + 15,
            wind_arrow_len * 0.55 * math.sin(theta_rad) + 12,
            f"Wind FROM: {wind_card} ({wind_deg:.0f}°)\nPlume TOWARD: {plume_card} ({travel_deg:.0f}°)",
            color="#38bdf8", fontsize=6.5, fontweight="bold"
        )

        max_reach = simulation_result.summary_zones[0].max_downwind_distance_m
        lim = max(350.0, max_reach * 0.85)
        ax.set_xlim(-lim * 0.6, lim)
        ax.set_ylim(-lim * 0.6, lim)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, linestyle="--", alpha=0.15, color="#64748b")
        ax.set_title("ATMOSPHERIC DISPERSION & THREAT ENVELOPE (Screening Gaussian Plume • T+120s)", color="#e2e8f0", fontsize=8, fontweight="bold", pad=4)
        ax.tick_params(colors="#94a3b8", labelsize=6.5)
        for spine in ax.spines.values():
            spine.set_color("#334155")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf

    def _render_evacuation_corridor_map(
        self,
        evac_plan: EvacuationPlanResponse,
        impact_result: ImpactAnalysisResult
    ) -> io.BytesIO:
        """Render high-resolution Dynamic Evacuation Corridor & Safe Muster Map."""
        fig, ax = plt.subplots(figsize=(6.5, 2.2), dpi=200)
        ax.set_facecolor("#090d16")
        fig.patch.set_facecolor("#090d16")

        # Plot candidate assembly points
        for ap in impact_result.assembly_points:
            color = "#10b981" if ap.status == "SAFE" else "#ef4444"
            marker = "^"
            ax.scatter([ap.coordinates[1]], [ap.coordinates[0]], color=color, s=70, zorder=8, edgecolors="white", linewidths=1.2, marker=marker)
            ax.text(ap.coordinates[1], ap.coordinates[0] + 0.0003, f"{ap.id} ({ap.status})", color=color, fontsize=6.5, fontweight="bold", ha="center")

        # Plot Evacuation Route
        prim = evac_plan.primary_evacuation_route
        if prim.route_coordinates and len(prim.route_coordinates) > 1:
            lats = [pt[0] for pt in prim.route_coordinates]
            lons = [pt[1] for pt in prim.route_coordinates]
            ax.plot(lons, lats, color="#10b981", linewidth=3.0, zorder=6)
            ax.scatter([lons[0]], [lats[0]], color="#f43f5e", s=60, zorder=10, edgecolors="white")
            ax.scatter([lons[-1]], [lats[-1]], color="#10b981", s=90, zorder=10, edgecolors="white", marker="*")

        ax.grid(True, linestyle="--", alpha=0.15, color="#64748b")
        ax.set_title(f"DYNAMIC SAFE EVACUATION CORRIDOR ({prim.recommended_assembly_point_name} • {prim.total_distance_m}m)", color="#e2e8f0", fontsize=8, fontweight="bold", pad=4)
        ax.tick_params(colors="#94a3b8", labelsize=6.5)
        for spine in ax.spines.values():
            spine.set_color("#334155")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf

    def generate_pdf_bytes(
        self,
        plant_info: Dict[str, Any],
        simulation_result: HazardSimulationResult,
        impact_result: ImpactAnalysisResult,
        evac_plan: EvacuationPlanResponse,
        resource_plan: ResourceOptimizationPlan,
        auth_record: Optional[AuthorizationRecordModel] = None,
        author_name: str = "SIH26162 Decision Support Engine",
        facility_ref: str = "PCH-ALPHA-04 (Demo Facility — Non-Statutory Evaluation)"
    ) -> bytes:
        """
        Generate a comprehensive, publication-grade industrial Emergency Pre-Plan PDF document
        strictly conforming to all final governance, layout, and freeze standards.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=44
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a")
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#475569")
        )
        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=6,
            spaceAfter=2.5
        )
        h2_style = ParagraphStyle(
            "Heading2_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=3.5,
            spaceAfter=1.5
        )
        body_style = ParagraphStyle(
            "Body_Custom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9.2,
            textColor=colors.HexColor("#334155")
        )
        body_bold = ParagraphStyle(
            "Body_Bold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9.2,
            textColor=colors.HexColor("#0f172a")
        )
        table_hdr = ParagraphStyle(
            "TableHdr",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9.2,
            textColor=colors.HexColor("#0f172a")
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#7f1d1d")
        )
        notice_style = ParagraphStyle(
            "NoticeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.8,
            textColor=colors.HexColor("#9a3412")
        )
        warning_style = ParagraphStyle(
            "WarningStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.8,
            textColor=colors.HexColor("#b91c1c")
        )

        story = []

        # Determine authorization state
        is_authorized = bool(auth_record and auth_record.status == "AUTHORIZED")
        doc_status = "AUTHORIZED (PROTOTYPE DEMO)" if is_authorized else (auth_record.status if auth_record else "PENDING_HUMAN_AUTHORIZATION")
        doc_version = auth_record.document_version if auth_record else "v0.1"

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # =========================================================================
        # PAGE 1: HEADER, SEVERITY, PROFILE, THREAT ZONES, MAP A, EXPOSURE IMPACT
        # =========================================================================

        # 1. Header Banner
        header_data = [
            [
                Paragraph("<b>SIH26162 — INDUSTRIAL EMERGENCY PRE-PLAN</b>", title_style),
                Paragraph(f"<b>INCIDENT ID:</b> {resource_plan.incident_id}<br/><b>DOCUMENT VERSION:</b> {doc_version} [{doc_status}]", subtitle_style)
            ],
            [
                Paragraph(f"<b>FACILITY:</b> {plant_info.get('name', 'PetroChem Complex Alpha')}<br/><b>PROTOTYPE FACILITY REF:</b> {facility_ref}", subtitle_style),
                Paragraph(f"<b>GENERATED:</b> {now_str}<br/><b>PREPARED BY:</b> SIH26162 Decision Support Engine", subtitle_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[330, 193])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 3.5))

        # 2. Executive Severity & Governance Status Banner
        risk = impact_result.risk_assessment
        risk_color = colors.HexColor(risk.color)
        
        gov_text = f"GOVERNANCE: {doc_status.replace('_', ' ')}" if not is_authorized else f"GOVERNANCE: AUTHORIZED BY {auth_record.approver_name.upper()} ({auth_record.approver_role})"
        risk_text = f"INCIDENT SEVERITY: {risk.risk_category} (SCORE: {risk.overall_score}/100) • {gov_text}"
        
        risk_banner = Table(
            [[Paragraph(f"<font color='white'><b>{risk_text}</b></font>", body_bold)]],
            colWidths=[523]
        )
        risk_banner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), risk_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(risk_banner)
        story.append(Spacer(1, 4))

        # 3. Incident Source, Chemical Hazard & Meteorological Profile
        story.append(Paragraph("1. INCIDENT SOURCE, CHEMICAL SDS & METEOROLOGICAL PROFILE", h1_style))
        meta = simulation_result.model_metadata or {}
        duration_min = meta.get("release_duration_min", 30)
        amb_temp = getattr(simulation_result, "ambient_temp_c", None)
        if amb_temp is None:
            amb_temp = meta.get("ambient_temp_c", 32.0)
        w_mode = simulation_result.weather_mode or "LIVE"
        w_src = simulation_result.weather_source or "Open-Meteo"
        
        wind_deg = simulation_result.wind_direction_deg
        travel_deg = (wind_deg + 180.0) % 360.0
        wind_card = simulation_result.wind_direction_cardinal
        plume_card = weather_service.deg_to_cardinal(travel_deg)

        scen_data = [
            [
                Paragraph("<b>Incident Type:</b>", body_bold),
                Paragraph(simulation_result.incident_type.replace("_", " ").title(), body_style),
                Paragraph("<b>Source Asset:</b>", body_bold),
                Paragraph(f"{simulation_result.source_asset_id} ({simulation_result.source_coordinates[0]:.4f}, {simulation_result.source_coordinates[1]:.4f})", body_style)
            ],
            [
                Paragraph("<b>Hazardous Substance:</b>", body_bold),
                Paragraph(f"<b>{simulation_result.chemical_name}</b>", body_bold),
                Paragraph("<b>Release Emission Rate:</b>", body_bold),
                Paragraph(f"{simulation_result.effective_release_rate_kg_s} kg/s (Duration: {duration_min} min)", body_style)
            ],
            [
                Paragraph("<b>Meteorological Wind Vector:</b>", body_bold),
                Paragraph(f"{simulation_result.wind_speed_kmh} km/h • <b>FROM:</b> {wind_card} ({wind_deg:.0f}°)", body_style),
                Paragraph("<b>Plume Propagation Vector:</b>", body_bold),
                Paragraph(f"Downwind Travel • <b>TOWARD:</b> {plume_card} ({travel_deg:.0f}°)", body_style)
            ],
            [
                Paragraph("<b>Ambient Temperature:</b>", body_bold),
                Paragraph(f"<b>{amb_temp}°C</b>", body_bold),
                Paragraph("<b>Weather Telemetry Source:</b>", body_bold),
                Paragraph(f"{w_mode} ({w_src}) • Stability: Class {simulation_result.atmospheric_stability}", body_style)
            ]
        ]
        scen_table = Table(scen_data, colWidths=[115, 145, 115, 148])
        scen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(scen_table)
        story.append(Spacer(1, 3.5))

        # 4. Hazard Threat Zones Table
        story.append(Paragraph("2. HAZARD THREAT ZONES (SCREENING GAUSSIAN DISPERSION ENVELOPE)", h1_style))
        zone_rows = [
            [
                Paragraph("<b>Zone Tier</b>", table_hdr),
                Paragraph("<b>Threshold Criterion</b>", table_hdr),
                Paragraph("<b>Downwind Reach</b>", table_hdr),
                Paragraph("<b>Crosswind Width</b>", table_hdr),
                Paragraph("<b>Threat Area</b>", table_hdr)
            ]
        ]
        for z in simulation_result.summary_zones:
            c_tag = "<font color='#b91c1c'>" if "Red" in z.name else ("<font color='#c2410c'>" if "Orange" in z.name else "<font color='#a16207'>")
            zone_rows.append([
                Paragraph(f"{c_tag}<b>{z.name}</b></font>", body_bold),
                Paragraph(z.threshold_label, body_style),
                Paragraph(f"{z.max_downwind_distance_m} m", body_style),
                Paragraph(f"{z.max_crosswind_width_m} m", body_style),
                Paragraph(f"{z.area_sq_m:,.0f} m²", body_style)
            ])
        zone_table = Table(zone_rows, colWidths=[115, 155, 85, 85, 83])
        zone_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(zone_table)
        story.append(Spacer(1, 3.5))

        # 5. Visual Map A: Hazard Dispersion Diagram
        map_a_buf = self._render_hazard_dispersion_map(simulation_result, plant_info)
        map_a_img = Image(map_a_buf, width=523, height=148)
        story.append(map_a_img)
        story.append(Spacer(1, 4))

        # 6. Exposure Impact Assessment Table (With Zero Exposure Rationale)
        story.append(Paragraph("3. POPULATION & INFRASTRUCTURE EXPOSURE IMPACT", h1_style))
        total_exposed = impact_result.red_zone_workers_count + impact_result.orange_zone_workers_count + impact_result.yellow_zone_workers_count
        
        exposure_note = ""
        if total_exposed == 0:
            exposure_note = "<br/><font color='#059669'><b>Exposure Assessment:</b> No active seeded worker coordinates intersected the calculated threat envelopes at simulation time.</font>"

        impact_summary = [
            [
                Paragraph("<b>Total Workers on Site:</b>", body_bold),
                Paragraph(f"{impact_result.total_workers_at_site} Personnel{exposure_note}", body_style),
                Paragraph("<b>Lethal Zone (Red) Exposed:</b>", body_bold),
                Paragraph(f"<font color='#b91c1c'><b>{impact_result.red_zone_workers_count} Workers</b></font>", body_bold)
            ],
            [
                Paragraph("<b>Severe Zone (Orange) Exposed:</b>", body_bold),
                Paragraph(f"{impact_result.orange_zone_workers_count} Workers", body_style),
                Paragraph("<b>Caution Zone (Yellow) Exposed:</b>", body_bold),
                Paragraph(f"{impact_result.yellow_zone_workers_count} Workers", body_style)
            ],
            [
                Paragraph("<b>Compromised Plant Assets:</b>", body_bold),
                Paragraph(f"{impact_result.affected_assets_count} of {impact_result.total_assets_at_site} Units", body_style),
                Paragraph("<b>Severed Road Segments:</b>", body_bold),
                Paragraph(f"{impact_result.blocked_roads_count} of {impact_result.total_roads_count} Segments", body_style)
            ]
        ]
        impact_table = Table(impact_summary, colWidths=[130, 131, 130, 132])
        impact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(impact_table)

        # Page Break -> Page 2
        story.append(PageBreak())

        # =========================================================================
        # PAGE 2: EVACUATION, LONG EGRESS WARNING, MAP B, TACTICAL RESOURCES
        # =========================================================================

        # 7. Dynamic Safe Evacuation Directives & Explainable Scoring
        story.append(Paragraph("4. DYNAMIC SAFE EVACUATION CORRIDOR & MUSTER DIRECTIVES", h1_style))
        prim_route = evac_plan.primary_evacuation_route
        score = prim_route.score_breakdown
        is_long_egress = prim_route.estimated_evac_time_min >= LONG_EGRESS_THRESHOLD_MIN

        walk_time_str = f"{prim_route.estimated_evac_time_min} minutes (at 1.2 m/s)"
        if is_long_egress:
            walk_time_str += f"<br/><font color='#b91c1c'><b>⚠ LONG EGRESS — HUMAN REVIEW REQUIRED (Threshold: &ge; {LONG_EGRESS_THRESHOLD_MIN:.0f}m)</b></font>"

        evac_data = [
            [
                Paragraph("<b>Designated Safe Assembly Point:</b>", body_bold),
                Paragraph(f"<font color='#065f46'><b>{prim_route.recommended_assembly_point_name}</b></font>", body_bold),
                Paragraph("<b>Exit Perimeter Gate:</b>", body_bold),
                Paragraph(prim_route.recommended_gate_name, body_style)
            ],
            [
                Paragraph("<b>Total Safe Egress Distance:</b>", body_bold),
                Paragraph(f"{prim_route.total_distance_m} meters", body_style),
                Paragraph("<b>Estimated Walk Time:</b>", body_bold),
                Paragraph(walk_time_str, body_style)
            ],
            [
                Paragraph("<b>Multi-Factor Scoring:</b>", body_bold),
                Paragraph(f"Safety: {int(score.safety_score*100)}% | Dist: {int(score.distance_score*100)}% | Rank: <b>{score.composite_score:.3f}</b>", body_style),
                Paragraph("<b>Route Clearance Status:</b>", body_bold),
                Paragraph(f"<font color='#059669'><b>{prim_route.route_status}</b></font>", body_bold)
            ],
            [
                Paragraph("<b>Selection Rationale:</b>", body_bold),
                Paragraph(score.selection_reason, body_style),
                Paragraph("<b>Avoided Blocked Roads:</b>", body_bold),
                Paragraph(", ".join(prim_route.avoided_blocked_roads) if prim_route.avoided_blocked_roads else "All internal segments clear", body_style)
            ]
        ]
        evac_table = Table(evac_data, colWidths=[130, 131, 130, 132])
        evac_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(evac_table)
        story.append(Spacer(1, 3.5))

        # Evaluated Alternatives & Rejection Analysis Table
        story.append(Paragraph("<b>Evaluated Muster Point Alternatives & Rejection Analysis:</b>", h2_style))
        cand_rows = [
            [
                Paragraph("<b>Candidate Assembly Point</b>", table_hdr),
                Paragraph("<b>Exit Gate</b>", table_hdr),
                Paragraph("<b>Distance</b>", table_hdr),
                Paragraph("<b>Safety</b>", table_hdr),
                Paragraph("<b>Status / Rejection Reason</b>", table_hdr)
            ]
        ]
        for c in evac_plan.candidate_routes:
            st_color = "<font color='#059669'>" if c.route_status == "SELECTED" else ("<font color='#0284c7'>" if c.route_status == "VIABLE_BACKUP" else "<font color='#dc2626'>")
            cand_rows.append([
                Paragraph(f"<b>{c.candidate_id}</b> ({c.target_assembly_point_id})", body_style),
                Paragraph(c.target_gate_id, body_style),
                Paragraph(f"{c.total_distance_m} m", body_style),
                Paragraph(f"{int(c.safety_score*100)}%", body_style),
                Paragraph(f"{st_color}<b>{c.route_status}:</b></font> {c.rejection_reason}", body_style)
            ])
        cand_table = Table(cand_rows, colWidths=[120, 70, 55, 45, 233])
        cand_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.0),
        ]))
        story.append(cand_table)
        story.append(Spacer(1, 3.5))

        # 8. Visual Map B: Evacuation Corridor Diagram
        map_b_buf = self._render_evacuation_corridor_map(evac_plan, impact_result)
        map_b_img = Image(map_b_buf, width=523, height=140)
        story.append(map_b_img)
        story.append(Spacer(1, 4))

        # 9. Tactical Emergency Resource Allocation & Suppression Strategy
        story.append(Paragraph("5. TACTICAL EMERGENCY RESOURCE DEPLOYMENT & SUPPRESSION STRATEGY", h1_style))
        
        tactical_notice = (
            "<b>DECISION-SUPPORT RECOMMENDATION — REQUIRES SITE/HSE VALIDATION:</b> "
            "All tactical quantities, PPE ensembles, suppression demands, and response actions are prototype computational recommendations "
            "and must be validated against facility ERDMP and competent safety authorities before operational deployment."
        )
        tactical_banner = Table([[Paragraph(tactical_notice, notice_style)]], colWidths=[523])
        tactical_banner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fdba74")),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(tactical_banner)
        story.append(Spacer(1, 3))

        fw = resource_plan.foam_water_requirements
        suppress_data = [
            [
                Paragraph("<b>Upwind Staging Standoff:</b>", body_bold),
                Paragraph(f"{resource_plan.standoff_upwind_m} meters", body_style),
                Paragraph("<b>Isolation Cordon Radius:</b>", body_bold),
                Paragraph(f"{resource_plan.isolation_perimeter_m} meters", body_style)
            ],
            [
                Paragraph("<b>Firewater Demand:</b>", body_bold),
                Paragraph(f"{fw.get('firewater_demand_lpm', 5000):,.0f} LPM", body_style),
                Paragraph("<b>Foam Concentrate Demand:</b>", body_bold),
                Paragraph(f"{fw.get('foam_concentrate_demand_liters', 0):,.0f} Liters (AFFF 3%)", body_style)
            ],
            [
                Paragraph("<b>Mandatory Entry PPE:</b>", body_bold),
                Paragraph(f"<font color='#b91c1c'><b>{fw.get('ppe_required', 'Level A Encapsulated SCBA')}</b></font>", body_bold),
                Paragraph("<b>Calculation Basis:</b>", body_bold),
                Paragraph(fw.get("formula_basis", "Derived from emission rate and chemical SDS"), body_style)
            ]
        ]
        suppress_table = Table(suppress_data, colWidths=[130, 131, 130, 132])
        suppress_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fed7aa")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#ffedd5")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(suppress_table)
        story.append(Spacer(1, 3))

        # Deployed Resource Units Table
        res_rows = [
            [
                Paragraph("<b>Unit Name & Type</b>", table_hdr),
                Paragraph("<b>Station</b>", table_hdr),
                Paragraph("<b>Staging Geolocation</b>", table_hdr),
                Paragraph("<b>Transit</b>", table_hdr),
                Paragraph("<b>ETA</b>", table_hdr),
                Paragraph("<b>Priority</b>", table_hdr)
            ]
        ]
        for r in resource_plan.recommended_resources:
            p_col = "<font color='#b91c1c'>" if r.priority == "IMMEDIATE" else ("<font color='#c2410c'>" if r.priority == "HIGH" else "<font color='#0284c7'>")
            res_rows.append([
                Paragraph(f"<b>{r.resource_name}</b><br/><font color='#64748b'>{r.assigned_role}</font>", body_style),
                Paragraph(r.current_station, body_style),
                Paragraph(r.staging_area_name, body_style),
                Paragraph(f"{r.distance_to_staging_m} m", body_style),
                Paragraph(f"<b>{r.estimated_arrival_min}m</b>", body_bold),
                Paragraph(f"{p_col}<b>{r.priority}</b></font>", body_bold)
            ])
        res_table = Table(res_rows, colWidths=[140, 45, 175, 55, 45, 63])
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.0),
        ]))
        story.append(res_table)

        # Page Break -> Page 3
        story.append(PageBreak())

        # =========================================================================
        # PAGE 3: INCIDENT COMMAND SNAPSHOT & PHASED SOP CHECKLISTS
        # =========================================================================

        story.append(Paragraph("6. INCIDENT COMMAND EXECUTIVE SUMMARY SNAPSHOT", h1_style))
        top_res = resource_plan.recommended_resources[0] if resource_plan.recommended_resources else None
        top_res_str = f"{top_res.resource_name} ({top_res.priority}, ETA: {top_res.estimated_arrival_min}m)" if top_res else "None"

        egress_summary_str = f"{prim_route.total_distance_m} m / {prim_route.estimated_evac_time_min} min"
        if is_long_egress:
            egress_summary_str += " <font color='#b91c1c'><b>(⚠ LONG EGRESS)</b></font>"

        snap_data = [
            [
                Paragraph("<b>Risk:</b>", body_bold),
                Paragraph(f"<font color='{risk.color}'><b>{risk.overall_score}/100 — {risk.risk_category}</b></font>", body_bold),
                Paragraph("<b>Chemical:</b>", body_bold),
                Paragraph(f"{simulation_result.chemical_name}", body_style)
            ],
            [
                Paragraph("<b>Personnel Exposed:</b>", body_bold),
                Paragraph(f"{total_exposed} workers (Red: {impact_result.red_zone_workers_count})", body_style),
                Paragraph("<b>Compromised Assets:</b>", body_bold),
                Paragraph(f"{impact_result.affected_assets_count} of {impact_result.total_assets_at_site} units", body_style)
            ],
            [
                Paragraph("<b>Blocked Roads:</b>", body_bold),
                Paragraph(f"{impact_result.blocked_roads_count} segments", body_style),
                Paragraph("<b>Primary Muster:</b>", body_bold),
                Paragraph(f"<b>{prim_route.recommended_assembly_point_name}</b>", body_style)
            ],
            [
                Paragraph("<b>Exit Gate:</b>", body_bold),
                Paragraph(prim_route.recommended_gate_name, body_style),
                Paragraph("<b>Egress Metrics:</b>", body_bold),
                Paragraph(egress_summary_str, body_style)
            ],
            [
                Paragraph("<b>Lead Tactical Resource:</b>", body_bold),
                Paragraph(top_res_str, body_style),
                Paragraph("<b>Firewater Demand:</b>", body_bold),
                Paragraph(f"{fw.get('firewater_demand_lpm', 5000):,.0f} LPM Water ({fw.get('foam_concentrate_demand_liters', 0):,.0f} L AFFF Foam)", body_style)
            ]
        ]
        snap_table = Table(snap_data, colWidths=[115, 145, 115, 148])
        snap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(snap_table)
        story.append(Spacer(1, 5))

        # 11. Phased Standard Operating Procedure (SOP) Action Checklists
        story.append(Paragraph("7. STANDARD OPERATING PROCEDURE (SOP) PHASED ACTION DIRECTIVES", h1_style))
        sop_data = []
        for chk in resource_plan.tactical_checklist:
            sop_data.append([Paragraph(f"<b>{chk.title}</b>", table_hdr)])
            for act in chk.actions:
                sop_data.append([Paragraph(f"• {act}", body_style)])
        sop_table = Table(sop_data, colWidths=[523])
        sop_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0, 0), (-1, -1), 2.2),
        ]))
        story.append(sop_table)

        # Page Break -> Page 4
        story.append(PageBreak())

        # =========================================================================
        # PAGE 4: DATA TRACEABILITY, REGULATORY DISCLAIMER, HUMAN AUTHORIZATION
        # =========================================================================

        # 12. Data Traceability & Screening Assumptions Matrix
        story.append(Paragraph("8. DATA TRACEABILITY & SCREENING MODEL ASSUMPTIONS", h1_style))
        trace_data = [
            [
                Paragraph("<b>Dispersion Physics:</b>", body_bold),
                Paragraph("Screening Gaussian Approximation with Pasquill-Gifford stability parameters", body_style),
                Paragraph("<b>Human Governance:</b>", body_bold),
                Paragraph("Mandatory HSE human review and authorization required prior to operational execution", body_style)
            ],
            [
                Paragraph("<b>Weather Telemetry:</b>", body_bold),
                Paragraph(f"{w_mode} Telemetry ({w_src}) • Recorded at {amb_temp}°C, {simulation_result.wind_speed_kmh} km/h", body_style),
                Paragraph("<b>Statutory Scope:</b>", body_bold),
                Paragraph("Decision-support prototype only; non-certified under statutory OISD/ALOHA rules", body_style)
            ],
            [
                Paragraph("<b>Terrain Modeling:</b>", body_bold),
                Paragraph("Simplified 2D/3D flat terrain representation with standard surface roughness (z₀ = 0.5m)", body_style),
                Paragraph("<b>Road & Worker Graph:</b>", body_bold),
                Paragraph("Prototype facility CAD/GIS network with obstacle avoidance pathfinding", body_style)
            ],
            [
                Paragraph("<b>Domino Cascade:</b>", body_bold),
                Paragraph("Screening cascade vulnerability evaluated across adjacent storage units & ESD headers", body_style),
                Paragraph("<b>Decision Audit Ref:</b>", body_bold),
                Paragraph(f"AUD-{datetime.utcnow().strftime('%Y%m%d')}-{resource_plan.incident_id[:8]} (Prototype Log)", body_style)
            ]
        ]
        trace_table = Table(trace_data, colWidths=[115, 145, 115, 148])
        trace_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]))
        story.append(trace_table)
        story.append(Spacer(1, 5))

        # 13. Non-Certified Prototype Decision-Support Disclaimer
        story.append(Paragraph("9. REGULATORY DISCLAIMER & PROTOTYPE NOTICE", h1_style))
        disclaimer_text = (
            "<b>PROTOTYPE DECISION SUPPORT — NON-CERTIFIED COMPUTATIONAL WORKFLOW:</b><br/>"
            "This emergency pre-plan document is prepared automatically by the SIH26162 Decision Support Engine. "
            "Dispersion envelopes, routing corridors, and tactical dispatches are computed for hackathon demonstration and decision-support prototyping only. "
            "This software does NOT claim certified ALOHA equivalence or statutory compliance. "
            "Operational tactical actions require validation against the facility's approved Emergency Response and Disaster Management Plan (ERDMP), applicable OISD/PESO standards, and competent statutory safety authorities."
        )
        disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[523])
        disclaimer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#f87171")),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        story.append(disclaimer_table)
        story.append(Spacer(1, 6))

        # 14. Human-In-The-Loop Authorization & Signature Block
        story.append(Paragraph("10. HUMAN-IN-THE-LOOP PRE-PLAN AUTHORIZATION & ENDORSEMENT", h1_style))

        if is_authorized:
            auth_time_str = auth_record.approval_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if auth_record.approval_timestamp else now_str
            auth_notes_str = f"<br/><b>Approval Notes:</b> {auth_record.approval_notes}" if auth_record.approval_notes else ""
            
            auth_box_content = [
                [
                    Paragraph(
                        f"<font color='#15803d'><b>DOCUMENT STATUS: AUTHORIZED (PROTOTYPE DEMO)</b></font><br/>"
                        f"<b>Document Version:</b> {doc_version}<br/>"
                        f"<b>Prepared by:</b> SIH26162 Decision Support Engine<br/>"
                        f"<b>Demonstration Approver:</b> <b>{auth_record.approver_name}</b><br/>"
                        f"<b>Role / Designation:</b> {auth_record.approver_role}<br/>"
                        f"<b>Authorization Record ID:</b> {auth_record.id}<br/>"
                        f"<b>Authorized At:</b> {auth_time_str}{auth_notes_str}",
                        body_style
                    ),
                    Paragraph(
                        "<b>DEMONSTRATION SIGNATURE BLOCK:</b><br/>"
                        "<font color='#059669' size='8.5'><b><i>✓ AUTHORIZED (PROTOTYPE DEMO)</i></b></font><br/>"
                        f"<font color='#334155'><b>{auth_record.approver_name}</b></font><br/>"
                        f"<font color='#64748b' size='7'>{auth_record.approver_role}</font><br/>"
                        "<font color='#94a3b8' size='6.5'>DEMO SIGNATURE — NOT A REAL SIGNATURE<br/>(Ready for PKI Digital Signature Integration)</font>",
                        body_style
                    )
                ]
            ]
            auth_table = Table(auth_box_content, colWidths=[310, 213])
            auth_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#22c55e")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 4.5),
            ]))
            story.append(auth_table)

        else:
            # Pending / Draft State
            auth_box_content = [
                [
                    Paragraph(
                        f"<font color='#b45309'><b>DOCUMENT STATUS: PENDING HUMAN AUTHORIZATION (Version {doc_version})</b></font><br/>"
                        f"<b>Prepared by:</b> SIH26162 Decision Support Engine<br/>"
                        f"<b>Approver:</b> Not provided (Pending Human Review)<br/>"
                        f"<b>Role / Designation:</b> Not provided<br/>"
                        f"<b>Authorization Record ID:</b> None (Draft State)<br/>"
                        f"<b>Human Authorization:</b> <font color='#dc2626'><b>REQUIRED</b></font><br/>"
                        f"<i>Document is in draft screening stage until human authorization is completed.</i>",
                        body_style
                    ),
                    Paragraph(
                        "<b>HUMAN AUTHORIZATION SIGNATURE:</b><br/><br/>"
                        "__________________________________________<br/>"
                        "<b>HSE Controller / Incident Commander</b><br/>"
                        "<font color='#b45309' size='7'><b>HUMAN AUTHORIZATION REQUIRED — NO SIGNATURE</b></font>",
                        body_style
                    )
                ]
            ]
            auth_table = Table(auth_box_content, colWidths=[310, 213])
            auth_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 4.5),
            ]))
            story.append(auth_table)

        # Build document with NumberedCanvas
        def canvas_maker(*args, **kwargs):
            c = NumberedCanvas(*args, **kwargs)
            c.incident_id = resource_plan.incident_id
            c.doc_version = doc_version
            c.doc_status = doc_status
            return c

        doc.build(story, canvasmaker=canvas_maker)
        buffer.seek(0)
        return buffer.getvalue()

preplan_service = PrePlanService()
