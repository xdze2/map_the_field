# Skill: `/validate-company` — Implementation Summary

## What's Built

### 1. Python Script: `tools/validate_web_presence.py`

**Purpose**: Extract and structure company data for Claude analysis

**Key Functions**:
- `find_ddg_file(siren)` — Locate latest DDG search JSON
- `load_ddg_data(filepath)` — Load and validate company_info metadata
- `load_naf_descriptions()` — Map NAF codes (72.20Z) → descriptions
- `extract_official_data(company_info, naf_map)` — Structure SIREN fields
- `prepare_results(results)` — Annotate DDG results with relevance/domain_type
- `save_validation_yaml(siren, slug, confidence, yaml_data)` — Write YAML report

**Invocation**:
```bash
source tools/venv/bin/activate
python tools/validate_web_presence.py 445199292
```

**Output**: 
- Prints human-readable analysis data to stderr
- Outputs JSON blob to stdout with structured official_data + web_results
- Claude reads both and generates YAML validation report

---

### 2. Claude Skill: `.claude/commands/validate-company.md`

**Invocation**: `/validate-company {SIREN}`

**Workflow**:
1. Run Python script → extracts official data + web results
2. Claude analyzes: name/location/activity match
3. Claude assigns confidence: `good` | `strange` | `wrong`
4. Claude generates full YAML report
5. Claude saves to: `data/company_data/web_presence_validations/{siren}_{slug}_{timestamp}_claude_{confidence}.yaml`

---

## How to Use

### Basic Usage

```
User: /validate-company 445199292

Expected output:
  [Python script runs]
  [Claude analyzes name/location/activity match]
  [YAML saved]
  
  Validation report saved to:
  data/company_data/web_presence_validations/445199292_autrement_20260425T143022_claude_wrong.yaml
```

### Accessing Results

```bash
# By confidence level
ls data/company_data/web_presence_validations/*_good_*.yaml
ls data/company_data/web_presence_validations/*_strange_*.yaml
ls data/company_data/web_presence_validations/*_wrong_*.yaml

# By author
ls data/company_data/web_presence_validations/claude_*.yaml
ls data/company_data/web_presence_validations/human_*.yaml

# Specific SIREN
ls data/company_data/web_presence_validations/*_445199292_*.yaml
```

---

## YAML Output Structure

```yaml
metadata:
  siren: "445199292"
  author: claude
  confidence: wrong  # good | strange | wrong
  timestamp: 2026-04-25T14:30:22Z
  ddg_search_date: 2026-04-25

official_data:
  siren: "445199292"
  name: AUTREMENT
  activity:
    code: 72.20Z
    description: "Recherche-développement en sciences humaines et sociales"
  legal_status:
    is_association: true
    is_ess: true
  location:
    address: "13 Rue du Château"
    postal_code: "81800"
    city: "RABASTENS"
  timeline:
    created: 1998-07-21
  employment:
    headcount_band: NN

web_presence:
  primary_url: "https://www.autrementconseilimmobilier.com"
  description: |
    All web results point to "Autrement Conseil Immobilier," a real estate 
    agency. This contradicts official registry showing a research organization.
  top_results:
    - rank: 1
      title: "Agence Immobilière Rabastens..."
      url: "https://www.autrementconseilimmobilier.com/"
      relevance: high
      domain_type: official_website

analysis:
  name_match: wrong
  location_match: wrong
  activity_match: wrong
  confidence_rationale: |
    WRONG: Official SIREN shows 72.20Z research organization; all web results 
    show real estate agency at different address. Likely data quality issue or 
    entity repurposing.
  key_observations:
    - "Official: research org; Web: real estate agency"
    - "Address mismatch: residential vs commercial"
    - "Activity codes differ fundamentally"
```

---

## Confidence Levels Explained

### **GOOD** ✓
- Official website found and matches company name exactly
- Location confirmed (city, postal code, address)
- Business activity aligns with NAF code
- Multiple sources confirm same info
- No contradictions

### **STRANGE** ⚠️
- Generic company name (hard to verify)
- Location partially aligns (city ok, address differs)
- Activity alignment unclear
- Limited web presence
- Could be active but low-visibility, or dormant

### **WRONG** ✗
- Web results describe completely different business
- Location substantially different
- Activity/sector fundamentally misaligned
- Evidence suggests stale/repurposed SIREN data
- No credible company presence found

---

## Requirements & Constraints

- **SIREN must have DDG search file**: `data/company_data/ddg_searches/ddg_search_{SIREN}_*.json`
- **DDG file must include metadata**: `company_info` field (added by updated search_duckduckgo.py)
- **Python dependencies**: click, yaml (already in venv)
- **Output directory created automatically**: `data/company_data/web_presence_validations/`

---

## Files Created

```
tools/
  validate_web_presence.py          NEW (executable Python script)

.claude/commands/
  validate-company.md               NEW (skill definition)

data/company_data/
  web_presence_validations/         NEW (output directory, auto-created)
```

---

## Next Steps

The skill is ready to use. To validate a company:

```bash
/validate-company 445199292
```

To batch-validate multiple SIRENs, you could extend this with a loop or create a separate batch script that calls `/validate-company` for each SIREN.
