# Skill: Validate Company Web Presence

## Overview
Analyzes DuckDuckGo (DDG) search results against official SIREN company data to validate web presence, extract company descriptions, identify website URLs, and assess confidence in the match.

## Purpose
Automate the triage of company research by comparing official registry data (SIREN API) with web search results (DuckDuckGo). Outputs structured assessments to guide manual review (detailled yaml file).


## Input
A single SIREN ID (e.g., `445199292`)

## Process

### Step 1: Locate and Load Data
- Find the latest DDG search file: `data/company_data/ddg_searches/ddg_search_{SIREN}_*.json`
- Extract `company_info` (full SIREN metadata) and `results` (web search results)
- If no DDG file exists, indicate data gap

### Step 2: Extract Key Official Data
From `company_info`, extract:
- **Company name**: `nom_complet`
- **Primary activity**: `activite_principale` (NAF code) + human-readable description
- **Address**: `siege.adresse`
- **Legal status**: `nature_juridique`, `complements.est_association`, `complements.est_ess`, etc.
- **Employee count**: `tranche_effectif_salarie`
- **Creation date**: `date_creation`
- **Status**: `etat_administratif` (A=active, F=closed, etc.)

### Step 3: Analyze Web Results
For each result in `results`:
- Extract URL domain, title, snippet
- Identify company mentions (exact name match, variations, acronyms)
- Check for location alignment (postal code, city from official data)
- Detect activity/sector alignment (web content vs NAF code)
- Flag contradictions (different business type, location mismatch, etc.)

### Step 4: Assess Confidence
Assign one of three confidence statuses:

#### **GOOD** ✓
- Web results clearly match official company name
- Location (city, postal code) aligns
- Business activity matches NAF code description
- Found credible company website or official listings
- No contradictions between official data and web results

#### **STRANGE** ⚠️
- Name match is partial or requires interpretation
- Location partially matches (e.g., city matches but address differs)
- Activity alignment is unclear or requires context
- Multiple different businesses with the same/similar name
- Website exists but doesn't clearly match the official company
- Limited or sparse web presence

#### **WRONG** ✗
- Web results describe a completely different business
- Location is substantially different (e.g., different city or postal code)
- Activity/sector is fundamentally different from NAF code
- No credible company presence found despite search results
- Evidence suggests SIREN data is stale, repurposed, or incorrect
- Web results show a different legal entity

### Step 5: Extract and Propose
Output structured assessment with:
- **Company description**: 1-2 sentences synthesizing official data + web presence
- **Website URL**: Most credible/active website found (or "None found")
- **Confidence status**: GOOD | STRANGE | WRONG
- **Evidence**: Key observations supporting the assessment

## Output Format

### Filename Structure
```
{siren}_{slug}_{date_iso}_{author}_{confidence}.yaml
```

Example: `445199292_autrement_20260425T124501_claude_wrong.yaml`

Where:
- **author**: `claude` (or `human` if manual review)
- **confidence**: `good` | `strange` | `wrong` (lowercase)
- **siren**: 9-digit SIREN ID
- **slug**: URL-friendly company name (lowercase, alphanumeric + dash)


### YAML Structure

```yaml
# Company Validation Report
metadata:
  siren: "445199292"
  author: claude
  confidence: wrong  # good | strange | wrong
  timestamp: 2026-04-25T12:34:56Z
  ddg_search_date: 2026-04-25

official_data:
  siren: "445199292"
  name: AUTREMENT
  name_short: null
  activity:
    code: "72.20Z"
    code_naf25: "72.20Y"
    description: "Research & development in human and social sciences"
    section: M
  legal_status:
    nature_juridique: "9220"
    legal_form: "Association"
    is_association: true
    is_ess: true
    is_entrepreneur: false
  location:
    address: "13 Rue du Château, Chez Sandrine Chavenon"
    postal_code: "81800"
    city: "Rabastens"
    department: "81"
    region: "76"
    coordinates:
      latitude: 43.819340987
      longitude: 1.7233809756
  establishment:
    total: 1
    active: 1
    siret: "44519929200019"
  timeline:
    created: 1998-07-21
    activity_started: 2008-01-01
    last_updated: 2026-04-24T19:47:10Z
  employment:
    headcount_band: NN  # NN = non-employer
    headcount_year: null

web_presence:
  primary_url: "https://www.autrementconseilimmobilier.com"
  url_confidence: wrong  # matches official data or not
  description: |
    All web results point to "Autrement Conseil Immobilier," a real estate 
    agency operating at 25 Quai des Escoussières. This contradicts official 
    registry data showing a 72.20Z research organization at a residential address.
  top_results:
    - rank: 1
      title: "Agence Immobilière Rabastens | Autrement Conseil Immobilier"
      url: "https://www.autrementconseilimmobilier.com/"
      snippet: "Retrouvez nos annonces immobilières Rabastens, Bessieres et Saint Sulpice..."
      relevance: high
      domain_type: official_website
    - rank: 2
      title: "Autrement Conseil Immobilier SARL - Agence immobilière..."
      url: "https://www.meilleursagents.com/agence-immobiliere/agence-autrement-conseil-immobilier-58924/"
      snippet: "25 quai des Escoussières, 81800 Rabastens..."
      relevance: high
      domain_type: business_directory

analysis:
  confidence_rationale: |
    WRONG: The official SIREN shows a 72.20Z research organization with no 
    employees and a residential address. All web results describe a real estate 
    agency (Autrement Conseil Immobilier) at a different address (25 Quai des 
    Escoussières). This indicates either SIREN data mismatch, entity 
    repurposing, or stale registry information.
  
  name_match: wrong
  name_match_notes: "Web results use 'Autrement Conseil Immobilier' (real estate), not 'AUTREMENT' (research org)"
  
  location_match: wrong
  location_match_notes: |
    Official: 13 Rue du Château, 81800 Rabastens
    Web: 25 Quai des Escoussières, 81800 Rabastens
    Same city, different addresses and different entity types.
  
  activity_match: wrong
  activity_match_notes: "Official activity is 72.20Z (R&D); web presence shows 6831Z (real estate agency)"
  
  key_observations:
    - "Official data shows association with zero employees"
    - "Web presence shows active real estate agency since at least 2016"
    - "Multiple independent sources confirm real estate business"
    - "Activity codes differ fundamentally (R&D vs real estate)"
    - "Address mismatch suggests different legal entities or SIREN repurposing"
  
  failure_modes: []  # e.g., ["generic_name", "shuttered_company", "name_collision"]

```

## Output Directory
All validation reports saved to: `/data/company_data/web_presence_validations/`

### Accessing Results
- By confidence: `ls data/company_data/web_presence_validations/*_good_*.yaml`
- By author: `ls data/company_data/web_presence_validations/claude_*.yaml`
- Single company: `ls data/company_data/web_presence_validations/*_445199292_*.yaml`

## Example YAML Outputs

### Example 1: GOOD Match
**File**: `claude_good_123456789_techforward.yaml`

```yaml
metadata:
  siren: "123456789"
  author: claude
  confidence: good
  timestamp: 2026-04-25T12:34:56Z
  ddg_search_date: 2026-04-25

official_data:
  siren: "123456789"
  name: TechForward SAS
  activity:
    code: "6202A"
    description: "IT consulting and management of information technology facilities"
  legal_status:
    nature_juridique: "5499"
    legal_form: "SAS"
    is_association: false
    is_ess: false
  location:
    address: "75 Rue de Rivoli"
    postal_code: "75001"
    city: Paris
    department: "75"
  timeline:
    created: 2015-03-10
  employment:
    headcount_band: "10-19"

web_presence:
  primary_url: "https://techforward.fr"
  url_confidence: good
  description: |
    TechForward is an active IT consulting firm with a well-maintained website,
    clear service offerings, and multiple industry listings. Web presence aligns
    perfectly with official registry data. Company specializes in digital transformation.

analysis:
  confidence_rationale: |
    GOOD: Official website found and matches company name exactly. Location 
    confirmed at official address. Business sector aligns with NAF code 6202A. 
    Multiple independent sources confirm same address and activity. No contradictions.
  
  name_match: good
  location_match: good
  activity_match: good

recommendations:
  triage_status: interesting
  triage_reason: "Tech × social impact firm, Paris-based, active web presence, confirmed details"
  manual_review_required: false
```

### Example 2: STRANGE Match
**File**: `claude_strange_987654321_services.yaml`

```yaml
metadata:
  siren: "987654321"
  author: claude
  confidence: strange
  timestamp: 2026-04-25T12:34:56Z

official_data:
  name: Services Conseil
  activity:
    code: "7022Z"
    description: "Management consulting"
  location:
    city: Lyon
    postal_code: "69000"

web_presence:
  primary_url: null
  url_confidence: strange
  description: |
    Multiple web results found but difficult to distinguish official company
    from competitors and directories. Generic name "Services Conseil" has
    many matches across France with varying addresses.

analysis:
  confidence_rationale: |
    STRANGE: Generic company name creates ambiguity. Business sector aligns 
    with official data, location roughly matches, but no definitive official 
    website. Could be active but low-visibility, or dormant entity.
  
  name_match: strange
  name_match_notes: "Generic name with multiple matches across France"
  activity_match: good

recommendations:
  triage_status: need_review
  triage_reason: "Generic name, ambiguous web presence; manual verification needed"
  manual_review_required: true
```

### Example 3: WRONG Match (Our Case)
**File**: `claude_wrong_445199292_autrement.yaml`

```yaml
metadata:
  siren: "445199292"
  author: claude
  confidence: wrong
  timestamp: 2026-04-25T12:34:56Z
  ddg_search_date: 2026-04-25

official_data:
  siren: "445199292"
  name: AUTREMENT
  activity:
    code: "72.20Z"
    description: "Research & development in human and social sciences"
  legal_status:
    is_association: true
    is_ess: true
  location:
    address: "13 Rue du Château, Chez Sandrine Chavenon"
    postal_code: "81800"
    city: "Rabastens"
  employment:
    headcount_band: "NN"  # non-employer

web_presence:
  primary_url: "https://www.autrementconseilimmobilier.com"
  url_confidence: wrong
  description: |
    All web results point to "Autrement Conseil Immobilier," a real estate 
    agency at 25 Quai des Escoussières. This contradicts official registry 
    data showing a 72.20Z research organization.

analysis:
  confidence_rationale: |
    WRONG: The official SIREN shows a 72.20Z research organization with no 
    employees at a residential address. All web results describe a real estate 
    agency (Autrement Conseil Immobilier) at a different address. SIREN data 
    may be stale, repurposed, or represent a data quality issue.
  
  name_match: wrong
  location_match: wrong
  activity_match: wrong
  
  key_observations:
    - "Official data: research org; web data: real estate agency"
    - "Address mismatch: residential vs commercial"
    - "Zero employees vs active business"

recommendations:
  triage_status: need_review
  triage_reason: "SIREN data does not match web presence; data quality issue or entity mismatch"
  manual_review_required: true
```

## Implementation Notes

- Run per SIREN (can be batched, but each produces independent assessment)
- Handle missing/incomplete DDG data gracefully (suggest re-running search)
- Detect and flag common failure modes:
  - Generic names (e.g., "Services", "Conseil") with many false positives
  - Shuttered companies with lingering web traces
  - Name collisions (multiple companies, same name)
- Confidence assessment is heuristic; ambiguous cases default to STRANGE
- Always recommend manual review for STRANGE and WRONG cases
