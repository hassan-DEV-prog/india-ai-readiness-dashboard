"""
Visualization Sub-package
=========================
Reusable, theme-consistent Plotly chart and map factories.
All functions return Plotly Figure objects — they do NOT call st.plotly_chart().
Streamlit pages import these functions and render them.
This separation keeps visualization logic testable and framework-agnostic.

Modules
-------
charts : Bar charts, line charts, scatter plots, heatmaps, radar charts
maps   : Choropleth state maps using GeoJSON + Plotly
"""
