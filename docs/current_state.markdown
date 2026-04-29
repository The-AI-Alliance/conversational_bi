---
layout: default
title: Decision Support: Current State
nav_order: 20
has_children: false
---

# Current State of Decision Support Analytics

A very common pattern for decision support is aggregating data from several sources, such as point-of-sale, inventory control or supply chain systems into a central enterprise data warehouse, such as Amazon RedShift, IBM DB2, Snowflake, or Microsoft Synapse. From there, a presentation layer can be built and published using any commerical analytics package, such as Micorosoft PowerBI, IBM Cognos, Tableau or Grafana:

![Traditional Decision Support](./assets/images/TradBI.png)

Using this model, a staff of business analysts can use their understanding of the enterprise data model and SQL to create views which can then be used to power interactive visualizations using the presentation layer to aid in decision support:

![Sample Visualiztion](./assets/images/Visualization.png)

The current decision support workflow:

1. Developing key performance indicators (KPIs) or implementing KPIs based on requirements handed down from other business groups.
2. Implementing those KPIs using SQL against the enterprise data model.
3. Implementing the visualizations based on the SQL in the presentation layer.