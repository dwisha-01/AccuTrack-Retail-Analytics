import os
import sys
import subprocess

# Step 1: Ensure fpdf2 is installed
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    print("PDF Generator: 'fpdf2' library not found. Installing now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except Exception as e:
        print(f"Error installing fpdf2: {e}")
        print("Please install fpdf2 manually using: pip install fpdf2")
        sys.exit(1)

class AccuTrackReport(FPDF):
    def header(self):
        # Omit header on the cover page (Page 1)
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "B", 8)
        self.set_text_color(100, 110, 120)
        self.cell(0, 10, "AccuTrack - ID-Persistent Retail Analytics Platform Documentation", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.set_draw_color(200, 200, 200)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        # Omit footer on the cover page (Page 1)
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_draw_color(220, 220, 220)
        self.line(10, 282, 200, 282)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        # Page number
        self.cell(0, 10, f"Page {self.page_no()} of {{nb}}", border=0, align="C")

    def chapter_title(self, num, title):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(30, 58, 138) # Deep blue (#1E3A8A)
        self.cell(0, 10, f"{num}. {title}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(3)

    def heading_2(self, text):
        self.set_font("helvetica", "B", 11)
        self.set_text_color(59, 130, 246) # Light blue (#3B82F6)
        self.cell(0, 8, text, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(2)

    def body_text(self, text):
        self.set_font("helvetica", "", 10)
        self.set_text_color(55, 65, 81) # Dark gray (#374151)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def bullet_point(self, title, description):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(31, 41, 55)
        self.write(6, f"  * {title}: ")
        self.set_font("helvetica", "", 10)
        self.set_text_color(55, 65, 81)
        self.write(6, f"{description}\n")
        self.ln(2)

    def code_block(self, text):
        self.set_fill_color(243, 244, 246) # Light gray bg (#F3F4F6)
        self.set_text_color(31, 41, 55)
        self.set_font("courier", "", 9)
        self.multi_cell(0, 5, text, border=1, fill=True)
        self.ln(4)

    def problem_solution_box(self, problem, solution):
        self.set_fill_color(254, 242, 242) # Soft red bg for warnings (#FEF2F2)
        self.set_draw_color(252, 165, 165) # Border light red (#FCA5A5)
        self.set_text_color(185, 28, 28)   # Text dark red
        self.set_font("helvetica", "B", 10)
        self.cell(0, 6, "  PROBLEM CHANNELS & SYMPTOM:", border="TLR", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.set_font("helvetica", "", 10)
        self.multi_cell(0, 5, f"  {problem}", border="LR", fill=True)
        
        self.set_fill_color(240, 253, 244) # Soft green bg for solution (#F0FDF4)
        self.set_draw_color(187, 247, 208) # Border light green (#BBF7D0)
        self.set_text_color(21, 128, 61)   # Text dark green
        self.set_font("helvetica", "B", 10)
        self.cell(0, 6, "  RESOLUTION & IMPLEMENTATION:", border="LR", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.set_font("helvetica", "", 10)
        self.multi_cell(0, 5, f"  {solution}", border="LBR", fill=True)
        self.ln(6)


def create_pdf_report():
    pdf = AccuTrackReport()
    pdf.alias_nb_pages()
    
    # ----------------------------------------------------
    # COVER PAGE
    # ----------------------------------------------------
    pdf.add_page()
    pdf.set_fill_color(248, 250, 252) # Off-white background
    pdf.rect(0, 0, 210, 297, "F")
    
    # Decorative Top Bar
    pdf.set_fill_color(30, 58, 138) # Deep Blue
    pdf.rect(0, 0, 210, 25, "F")
    
    pdf.ln(50)
    
    # Title
    pdf.set_font("helvetica", "B", 32)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 15, "ACCUTRACK", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    # Subtitle
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(59, 130, 246)
    pdf.cell(0, 10, "ID-Persistent Retail Analytics Platform", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    pdf.ln(10)
    
    # Divider
    pdf.set_draw_color(59, 130, 246)
    pdf.set_line_width(1)
    pdf.line(40, 100, 170, 100)
    
    pdf.ln(25)
    
    # Description short
    pdf.set_font("helvetica", "I", 11)
    pdf.set_text_color(75, 85, 99)
    pdf.multi_cell(0, 6, "A technical overview of the implementation, machine learning pipelines, "
                         "real-world engineering challenges faced, and resolutions implemented in the "
                         "AcuTrack multi-camera tracking system.", align="C")
    
    pdf.ln(70)
    
    # Metadata footer on cover page
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 6, "Project Status: Active Development / Production Prototype", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 6, "Technologies: YOLOv8 | StrongSort | OSNet | LSTM Autoencoder | Flask", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 6, "Document Version: 1.0 (August 2026)", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    # ----------------------------------------------------
    # PAGE 2: Introduction & Vision Pipeline
    # ----------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("1", "Executive Summary & Introduction")
    pdf.body_text(
        "AccuTrack is an AI-powered retail analytics and crowd intelligence platform. In modern "
        "retail environments, understanding customer movement - such as entry rates (footfall), average "
        "dwell times in specific zones, and behavior trajectories - is critical to improving store layouts, "
        "optimizing staff distribution, and ensuring security.\n\n"
        "The system processes multiple video streams concurrently, performing real-time person detection, "
        "multi-object tracking, cross-camera identity matching (re-identification), and trajectory anomaly "
        "detection. The results are broadcast via SocketIO to a web-based dashboard that provides real-time "
        "occupancy statistics, alerts, and historical statistics."
    )
    
    pdf.heading_2("Core System Features:")
    pdf.bullet_point("Real-time Multi-stream Tracking", "Processes 7 Wildtrack camera feeds simultaneously.")
    pdf.bullet_point("Zone Analytics", "Calculates footfall counts, current occupancies, and average dwell times for zones.")
    pdf.bullet_point("Cross-Camera Re-ID", "Maintains consistent identity tracking as users move between camera fields of view.")
    pdf.bullet_point("Behavior Anomaly Detection", "Uses deep learning to score trajectories and flag unusual movements (loitering).")
    
    pdf.ln(5)
    pdf.chapter_title("2", "The Machine Learning Pipeline")
    pdf.body_text(
        "AccuTrack achieves tracking and behavioral analysis by cascading four core machine learning "
        "and computer vision modules:"
    )
    
    pdf.bullet_point("YOLOv8 (Object Detection)", 
                     "Detects persons in each frame using a YOLOv8 nano model (optimized as ONNX for CPU). "
                     "It outputs bounding boxes around individuals with confidence scores.")
                     
    pdf.bullet_point("StrongSort (Multi-Object Tracking)", 
                     "Maintains frame-to-frame associations. It links detections over consecutive frames within a "
                     "single camera view, predicting movements using a Kalman filter and generating local track IDs.")
                     
    pdf.bullet_point("OSNet (Omni-Scale Re-ID Network)", 
                     "Extracts a high-dimensional (512-float) feature vector (embedding) representing a person's visual "
                     "appearance. This embedding is used to associate local tracks from different cameras to a unified Global ID.")
                     
    pdf.bullet_point("LSTM Autoencoder (Anomaly Detection)", 
                     "Analyzes visitor trajectory sequences. Normal movement patterns have low reconstruction errors "
                     "when passed through the trained encoder-decoder network. High reconstruction error indicates "
                     "irregular movement (e.g. loitering, trespassing, or panic).")
    
    # ----------------------------------------------------
    # PAGE 3: Detailed Logic & Algorithms
    # ----------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("3", "Detailed Logic & Algorithms")
    
    pdf.heading_2("1. Dwell Time and Footfall Calculation")
    pdf.body_text(
        "Every camera stream defines specific rectangular areas corresponding to retail zones (e.g. Entrance, "
        "Food Court, Exit Corridor). For each active track, the system calculates the center point of its bounding box "
        "and evaluates if it lies within a zone's coordinates:\n"
        " - Entry: When a track enters a zone for the first time, the entry timestamp is recorded.\n"
        " - Dwell time: The running difference between the current frame timestamp and the entry timestamp.\n"
        " - Exit & Footfall: When a track exits the zone or disappears, the final dwell time is computed and added "
        "to a running averages list. The zone's historical footfall counter is incremented."
    )
    
    pdf.heading_2("2. Cross-Camera Re-ID Gallery Logic")
    pdf.body_text(
        "To track a customer across the entire store layout, we maintain a global gallery of known customer embeddings. "
        "When a new local track starts on any camera:\n"
        " 1. OSNet extracts its feature embedding.\n"
        " 2. The embedding is compared against all registered identities in the global gallery using cosine distance.\n"
        " 3. If the minimum distance is below a matching threshold (0.45) and is unambiguous (meaning it does not closely "
        "match multiple candidates), the local track is merged with the existing Global ID.\n"
        " 4. Otherwise, a brand new Global ID is created and added to the gallery."
    )
    
    pdf.heading_2("3. LSTM Autoencoder Anomaly Score")
    pdf.body_text(
        "The LSTM Autoencoder monitors spatial trajectories. It processes coordinates as relative displacements "
        "over a sliding window of 30 frames. The encoder compresses the sequence, and the decoder attempts to "
        "recreate it. The reconstruction loss is calculated as Mean Squared Error (MSE):\n"
    )
    pdf.code_block("  Reconstruction Loss (MSE) = Mean( (X_original - X_reconstructed)^2 )\n"
                   "  Anomaly Score = ML_Weight * MSE + Rule_Weight * (Dwell_Time / Loiter_Limit)")
    pdf.body_text(
        "If the combined anomaly score exceeds the anomaly threshold, a real-time warning is triggered in the GUI."
    )
    
    # ----------------------------------------------------
    # PAGE 4: Engineering Challenges & Technical Resolutions
    # ----------------------------------------------------
    pdf.add_page()
    pdf.chapter_title("4", "Engineering Challenges & Resolutions")
    pdf.body_text(
        "Deploying multiple deep learning models in real-time across 7 camera streams revealed "
        "several edge cases. Below are the key problems faced and how we resolved them:"
    )
    
    pdf.problem_solution_box(
        "Cross-Camera Global ID Collisions\n"
        "Initially, when a new track was registered but its embedding wasn't ready yet, the tracker fell back "
        "to the local raw track_id. Because StrongSort on Camera 1 and Camera 2 both number tracks starting from 1, "
        "two different people ended up sharing the same Global ID=1, resulting in merged target locks and blended gallery statistics.",
        
        "Namespaced Local ID Fallbacks\n"
        "We introduced camera-namespaced negative integers as temporary fallback IDs (e.g., fallback ID = "
        "-(camera_index * 1000 + local_track_id)). Since all registered global gallery IDs are positive integers "
        "starting from 1, these negative fallbacks can never collide with each other or existing gallery IDs."
    )

    pdf.problem_solution_box(
        "Embedding Degradation (Blurry Templates)\n"
        "The gallery previously maintained a running average of matching embeddings for each Global ID. "
        "However, averaging embeddings taken from different angles (e.g., front-view vs top-view) produced a "
        "'blurry' average vector that didn't match any viewpoint well, causing the system to lose track of customers "
        "when they changed angles.",
        
        "Multi-Template Gallery Matching\n"
        "Instead of keeping a single average embedding, the gallery now stores up to 6 distinct templates (historical captures) "
        "per person. Comparisons are made against the best-matching (minimum distance) template. This allows robust "
        "matching across multiple distinct viewing angles."
    )

    pdf.problem_solution_box(
        "Thread Lock Contention & Frame Stutter\n"
        "Originally, a single global YOLO lock and behavior lock was shared across all camera threads. "
        "This meant camera threads spent most of their time waiting for locks, dropping frames, and falling behind "
        "real-time speed.",
        
        "Lock Splitting and Dedicated Model Instances\n"
        "We modified the engine to run independent YOLO models and separate locks for each camera thread. "
        "Additionally, we introduced on-demand thread initialization - camera streams only start executing "
        "and consuming resources when the operator first views them."
    )

    # ----------------------------------------------------
    # PAGE 5: Engineering Challenges Continued & Database Schema
    # ----------------------------------------------------
    pdf.add_page()
    pdf.problem_solution_box(
        "Ghost Tracks and ID Fragmentation\n"
        "With a low detection confidence threshold (0.20) and high tracking max_age (60 frames), the system "
        "suffered from ghost tracks (random shapes registered as stationary people) and ID fragmentation "
        "(a person walking out of view and returning registered as a new ID).",
        
        "Threshold Tuning\n"
        "We tuned the YOLO confidence threshold to 0.35 to eliminate false detections. The tracking max_age "
        "was tuned to 20/30 frames (about 4 to 6 seconds), which eliminates ghost track persistence while keeping "
        "temporarily occluded targets linked."
    )
    
    pdf.chapter_title("5", "Database Schema Design")
    pdf.body_text(
        "To enable historical analysis, footfall tracking, and alert logging, we transitioned the "
        "application from in-memory arrays to a SQL-based database using SQLAlchemy. Below is the mapping "
        "of the core schema tables:"
    )
    
    # Table description
    pdf.bullet_point("cameras", "Registers configured streams, URLs, status, and metadata.")
    pdf.bullet_point("zones", "Defines the specific retail monitoring locations (coordinates, capacities, colors).")
    pdf.bullet_point("tracked_persons", "Stores all unique re-identified visitors, when they were seen, and suspicious status.")
    pdf.bullet_point("person_embeddings", "Stores raw high-dimensional embeddings mapping back to unique users for Re-ID.")
    pdf.bullet_point("dwell_times", "Logs visit intervals (entry, exit, duration) for each person per zone.")
    pdf.bullet_point("tracked_persons_history", "Stores high-resolution coordinates for heatmaps and model re-training.")
    pdf.bullet_point("occupancy_snapshots", "Records zone/camera occupancies periodically for dashboard chart loading.")
    pdf.bullet_point("alerts", "Persists security and crowd limit violations for auditor lookup.")
    
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "Verification & Future Improvements", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.body_text(
        "By writing these statistics to a database, the frontend dashboard can load historical trends "
        "(e.g., peak footfall hours, zone popularity indices, average dwell times by week day). "
        "This lays the groundwork for cloud deployments, advanced customer behavior analytics dashboards, "
        "and multi-store analytics integration."
    )
    
    # Save the file
    pdf.output("AccuTrack_Project_Documentation.pdf")
    print("Database Report: Successfully generated 'AccuTrack_Project_Documentation.pdf'!")

if __name__ == "__main__":
    create_pdf_report()
