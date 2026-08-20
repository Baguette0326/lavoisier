# LinkedIn Caption Draft

## Short Version

I built Lavoisier, a local decision-support prototype for carbon-capture MOF screening.

The app ranks a controlled CRAFTED CO2/N2 GCMC slice, enriches records with CoRE MOF structural provenance, and uses target-specific ML estimates to help flag promising or suspicious candidate records. The goal is not to claim a new best material, but to make screening decisions more transparent: what was compared, what was filtered out, what evidence was used, and where the assumptions are weak.

This project helped me connect chemical-engineering judgment with data engineering, reproducible workflows, and reviewable AI-assisted analysis.

## More Technical Version

I built Lavoisier, a local Streamlit app and backend pipeline for carbon-capture MOF screening.

The project parses a controlled CRAFTED CO2/N2 GCMC slice, ranks candidates using explicit engineering metrics, attaches provenance and comparability metadata, enriches records with CoRE MOF 2014 descriptors where joinable, and runs descriptor-based ML estimates for candidate triage. It also exports transformation logs so each result can be traced back to source files, filters, ranking weights, generated artifacts, and limitations.

The point is not to automate scientific judgment. It is to make material-screening review more reproducible and easier to explain.
