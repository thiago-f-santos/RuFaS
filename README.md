[![Flake8](https://img.shields.io/badge/Flake8-passed-brightgreen)](https://github.com/RuminantFarmSystems/MASM/actions/workflows/combined_format_lint_test_mypy.yml)
[![Pytest](https://img.shields.io/badge/Pytest-passed-brightgreen)](https://github.com/RuminantFarmSystems/MASM/actions/workflows/combined_format_lint_test_mypy.yml)
[![Coverage](https://img.shields.io/badge/Coverage-99%25-brightgreen)](https://github.com/RuminantFarmSystems/MASM/actions/workflows/combined_format_lint_test_mypy.yml)
[![Mypy](https://img.shields.io/badge/Mypy-1164%20errors-red)](https://github.com/RuminantFarmSystems/MASM/actions/workflows/combined_format_lint_test_mypy.yml)


# RuFaS: Ruminant Farm Systems

**RuFaS** is an open-source, next-generation, whole-farm modeling environment that simulates dairy farm production and environmental impact. It is designed to support research, innovation, and sustainable decision-making in ruminant animal agriculture. 

---

### 🌿 Fork Rationale: RuFaS Brasil (Southern Hemisphere & National Regionalization)

- **Fork Rationale:** This fork adapts RuFaS for tropical and subtropical dairy production systems in Brazil and the Southern Hemisphere. It enables realistic astronomical photoperiods for negative latitudes and modularizes regional identification using official IBGE codes.
- **Lineage:** Forked from upstream RuFaS v1.0.5 (`dev` branch, commit `717f47203d3a881eaa29fb8b0c5bb7a27deb79e1`).
- **Material Deviations:**
  1. *Signed Latitude & Photoperiod:* Supports negative latitudes (`latitude` in `field_properties`) so that solar declination daylength correctly models summer in Dec–Feb and winter in Jun–Aug. Maintains bidirectional synchronization with `absolute_latitude`.
  2. *Regional Modularization:* Adds `country` (ISO 3-letter code) and `region_code` to `config_properties`. Generalizes purchased feed emissions lookup and Wood lactation curve state mapping with support for 2-digit UF and 7-digit municipality IBGE codes, with neutral additive fallback (`{"l": 0.0, "m": 0.0, "n": 0.0}`).
  3. *Zero-breakage Backward Compatibility:* Retains full compatibility with legacy US scenarios (`FIPS_county_code`, `absolute_latitude`).
- **Comparability Note:** Simulation results for US scenarios (`country: "USA"` or legacy configs) remain 100% identical and directly comparable to upstream RuFaS. For Brazilian and Southern Hemisphere scenarios, crop phenology and photoperiod-driven processes reflect the real Southern Hemisphere calendar, meaning seasonal timing intentionally diverges by 6 months from unpatched upstream simulations.
- **Documentation:** See the [Guia de Uso do RuFaS Brasil](docs/usage_brasil.md) for full configuration instructions and examples.
- **Disclaimer:** This fork is an independent research adaptation and does not imply official endorsement by the upstream RuFaS project.

---

### 🌍 Vision

A world where the continuous generation and sharing of knowledge about ruminant production systems [^note] empower understanding and decision making to achieve socio-economic well-being and environmental sustainability.
[^note]:  **RuFaS** is currently focused on dairy cattle production systems.


---

### 🎯 Mission

To develop, maintain, and share an open, modular simulation platform that connects scientific research with real world decision making. Equip scientists, farmers, and other stakeholders with tools to understand, evaluate, and improve the environmental, economic, and social outcomes of ruminant farming systems by integrating transparent models, diverse data, and collaborative contributions.
 

---

### 🧪 Scientific Foundation

RuFaS is grounded in peer-reviewed science and collaborative development. It is maintained by a diverse community of researchers, developers, and stakeholders committed to transparency, reproducibility, and continuous improvement.

---

### ♟️ Strategy

The strategic direction of RuFaS, including its vision, mission, strategic pillars, values, and operating principles, is described in [Strategy.md](Strategy.md).

---

### 🚀 Getting Started

1. **Install Python 3.12 or 3.13** - Make sure you have one of these versions installed on your system.
2. **Set up a virtual environment**
```bash
python -m venv venv
source venv/bin/activate on Mac/Linux or venv\Scripts\activate on Windows
```
3. **Install dependencies**
```bash
pip install .
```
4. **Enable output display** - Navigate to `output/output_filters/` and rename `_csv_all_variables.txt` → `csv_all_variables.txt` (remove the leading underscore).
5. **Run RuFaS**
```bash
python main.py
```
6. **Learn more** if you have further questions read through the documentation on our [GitHub Pages site](https://ruminantfarmsystems.github.io/RuFaS/) or watch our [onboarding video series](https://www.youtube.com/playlist?list=PLqq6i4QOoueR-a2mxVX3Gc78s1wvTRfr1).
7. **RuFaS Brasil (Hemisfério Sul e Regionalização)** - Consulte o [Guia de Uso do RuFaS Brasil](docs/usage_brasil.md) para detalhes sobre configuração de latitude negativa, códigos IBGE e parametrização nacional.

---

### 🤝 How to Contribute

RuFaS welcomes coding and noncoding contributions from individuals demonstrating interest and commitment to our program standards. You can:
- 🧪 Test features and report bugs
- 💡 Suggest new features or improvements
- 🗣️ Engage in scientific discussions and peer reviews
- 💻 Submit code, documentation, or scientific literature
- 🧰  Help with user support and onboarding
- 🎨  Design user interfaces or visual assets
- 📣  Promote RuFaS within your networks

> Please see the [![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md) code of conduct and [CONTRIBUTING.md](https://github.com/RuminantFarmSystems/RuFaS/blob/dev/CONTRIBUTING.md?plain=1) for full details.

> For prerequisites and testing read the [PREREQUISITES](https://ruminantfarmsystems.github.io/RuFaS/_wiki/Github-Actions.html) and [End-to-End Testing](https://ruminantfarmsystems.github.io/RuFaS/_wiki/End%E2%80%90to%E2%80%90End-Testing.html) files.

---

### 📜 License

RuFaS is licensed under GPLv3. See the [COPYING.md](https://github.com/RuminantFarmSystems/RuFaS/pull/2369) and [COPYING.LESSER.md](https://github.com/RuminantFarmSystems/RuFaS/pull/2369) files for details.

---

## 📬 Contact

For questions, sponsorship inquiries, or collaboration proposals, please email contact@rufas.org.

---

## 🧑‍🔬 Acknowledgements

Thanks to all the [individuals](https://www.rufas.org/the-team) and [organizations](https://www.rufas.org/partners) that contributed to RuFaS development and maintenance in the past and continue to contribute today. Contributions to the RuFaS GitHub repository are recorded [here](https://github.com/RuminantFarmSystems/RuFaS/graphs/contributors).
