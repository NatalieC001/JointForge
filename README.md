# JointForge 🔧
Precision Keyed Joints for 3D Printable Models
Copyright (c) 2024-2026 NatalieC. All Rights Reserved.

*Developed as part of the [Hummingbird in Paper](https://nataliec001.github.io/Hummingbird-in-Paper/) project.*

[![version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange.svg)](https://www.blender.org/)
[![license](https://img.shields.io/badge/license-GPL--3.0-orange.svg)](https://www.gnu.org/licenses/gpl-3.0)

https://github.com/user-attachments/assets/1ef86217-f74e-4104-ab48-3fa862080085


---

## 🌿 High-Fidelity Fabrication
**JointForge** is a Blender add-on that lets you roll with the big models. It automatically creates precision keyed joints for splitting and reassembling 3D designs. Whether your model is too "large" for one hit or you’re looking for a cleaner multi-material trip, JointForge ensures everything fits together perfectly.

### Why JointForge?
* ** Large 3D Prints:** Split models that exceed your printer's build volume.
* ** Multi-Material Hits:** Create clean assembly points for different filaments or resins.
* ** Paint-Friendly:** Break down complex models to get into every "nook and cranny."
* ** Modular Stash:** Create collapsible or interlocking designs for better storage.

---

##  Features
* **One-Click Spark:** Select your mesh, choose a slicing plane, and generate matching joints instantly.
* **Adjustable Strains:** Fully customize key size, depth, and fit tolerance for a smooth connection.
* **Flexible Assignment:** Choose which part gets the peg (male) and which gets the notch (female).
* **Clean Hits (Non-Destructive):** Original mesh remains untouched; new parts are stashed in a dedicated collection.
* **Universal Vibe:** Works with any manifold mesh—from organic sculpts to hard-surface geometry.

---

##  Installation
1.  **Download** `JointForge2.py`.
2.  **In Blender:** Navigate to `Edit → Preferences → Add-ons → Install`.
3.  **Enable:** Select the file and check the box to activate.
4.  **Find it:** Open the **3D Viewport sidebar** (Press **N**) and look for the **JointForge** tab.

---

##  Basic Workflow
1.  **Prepare the Stash:** Ensure your mesh is manifold (watertight). Position a **Plane Object** exactly where you want the split.
2.  **Pack the Settings:**
    * **Key Size (mm):** Width of the square peg/hole.
    * **Key Depth (mm):** How deep the joint penetrates.
    * **The Gap (mm):** Clearance for easy assembly (0.2mm is the "sweet spot" for FDM).
3.  **Spark It:** Click **"Generate Joints"**.
4.  **Check the Results:** Your original mesh is hidden, and two new objects appear in a `[ModelName]_Parts` collection.

---

## 📊 Recommended Settings
| Printer Type | Key Size | Key Depth | Gap (Clearance) | Note |
| :--- | :--- | :--- | :--- | :--- |
| **FDM (0.4mm nozzle)** | 5.0mm | 4.0mm | 0.2mm | Standard chill fit |
| **FDM (0.6mm nozzle)** | 6.0mm | 5.0mm | 0.3mm | Looser for thicker layers |
| **Resin / SLA** | 4.0mm | 3.0mm | 0.1mm | Tight, high-res precision |
| **Large Format** | 10.0mm | 8.0mm | 0.4mm | Structural strength |

---

## 🔧 Technical Details
* **Slicing:** Uses the `Bmesh bisect` method with automatic face filling.
* **Boolean Solver:** Utilizes the **Exact** solver (Blender 4.2+) for error-free unions.
* **Gap Logic:** The female notch is mathematically scaled by a $(size + gap) / size$ factor.

---

🐛 Troubleshooting "Bad Trips"
"Boolean operation failed"
Your mesh might be "dirty." Check for non-manifold geometry: Edit Mode → Select → All by Trait → Non Manifold. Clean your stash before you split it! No one likes a messy joint 😉. 

"Parts are too tight"
If your parts don't fit after printing, don't force it—stay relaxed. Increase your Fit Gap by 0.1mm and re-roll the generation.

---

## 📝 Future Road Map
* [ ] **New Shapes:** Circular and hexagonal key options...ball joints hmmmm???.
* [ ] **Dovetail Style:** For joints that lock without glue.

---

[![license](https://img.shields.io/badge/license-GPL--3.0-orange.svg)](https://www.gnu.org/licenses/gpl-3.0)
**GPL License** – Free to download and modify, but any shared versions must stay under this same license.

*Made with ❤️ for the 3D Printing Community.*
