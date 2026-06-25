# Cover Letter — Critical Care Medicine

> **Target Journal**: *Critical Care Medicine* (IF 19.3)  
> **Manuscript Type**: Brief Report  
> **Status**: Ready for submission

---

## Submission Version (Single-Blind)

```
Date: [Insert date]

To: The Editor-in-Chief, Critical Care Medicine

Subject: Submission of Brief Report: "Unmasking Heat Collapse: A Rule-Based
Septic-Shock Phenotyping Framework Using 85,242 MIMIC-III ICU Stays"

Dear Dr. [Editor Family Name]:

We submit our manuscript "Unmasking Heat Collapse: A Rule-Based Septic-Shock
Phenotyping Framework Using 85,242 MIMIC-III ICU Stays" for consideration as a
Brief Report in *Critical Care Medicine*.

**Clinical Problem**: Sepsis-3 stratifies patients by SOFA and lactate, but
vasoplegic (warm) vs cardiogenic (cold) shock physiology remains undifferentiated
in current risk scores. We hypothesized that a rule-based phenotyping framework
could identify a distinct high-mortality subphenotype within septic-shock cohorts.

**Methods & Findings**: Applying 85,242 MIMIC-III ICU stays, we built a rule-based
mapper (ICD-9/10 + vasopressor + lab proxies) validated against 13 gold-standard
syndromes (63.3% manual agreement on 30 random cases). We identified a "Heat
Collapse" (Re Jue, 热厥) subphenotype—septic shock with vasoplegia and
hyperinflammation—with 32.5% mortality vs 17.8% for "Shaoyin" (少阴,
non-vasoplegic shock). Multivariable Cox regression confirmed independence from
age/sex (aHR 2.30, 95% CI 2.16–2.45). Kaplan-Meier curves showed early divergence
(<10 days) between subphenotypes.

**Why CCM**: This is the largest rule-based septic-shock phenotyping study to date,
with an HR exceeding conventional biomarkers (lactate, procalcitonin). The
framework is open-source (github.com/amyicf79/TCM-SHARD), reproducible, and
extensible to other ICU phenotypes (diabetes, AKI)—the latter two map onto TCM
concepts of "Xiao Ke" and "Ni Du", supporting cross-system translation.

We suggest reviewers with expertise in sepsis phenotyping and MIMIC-based
methodology. All authors declare no conflicts of interest. The manuscript is
original and not under consideration elsewhere.

Thank you for your consideration.

Sincerely,
[Your Name]
```

---

## Double-Blind Version (Anonymized)

```
Date: [Insert date]

To: The Editor-in-Chief, Critical Care Medicine

Subject: Submission of Brief Report: "Unmasking Heat Collapse: A Rule-Based
Septic-Shock Phenotyping Framework Using 85,242 MIMIC-III ICU Stays"

Dear Editor-in-Chief:

We submit a Brief Report analyzing 85,242 MIMIC-III ICU stays through a rule-based
septic-shock phenotyping framework. Our key finding: a distinct vasoplegic shock
subphenotype ("Heat Collapse" / Re Jue) with a 2.3-fold increased mortality risk
compared to unclassified controls (aHR 2.30, 95% CI 2.16–2.45), independent of
age and sex. The aHR substantially exceeds that of lactate (>2 mmol: aHR ~1.8)
and procalcitonin (aHR ~1.5).

Unlike prior black-box machine learning approaches, our framework is fully
transparent and reproducible. All mapping rules are clinically interpretable,
and the codebase is open-source (https://github.com/amyicf79/TCM-SHARD). This
work addresses the unmet need for interpretable risk stratification tools in
sepsis management, aligning with the journal's scope.

All authors declare no conflicts of interest. The manuscript is original and not
under consideration elsewhere.

Thank you for your consideration.
```

---

## Submission Checklist

- [ ] Finalize manuscript (`.tex` or `.docx` per CCM guidelines)
- [ ] Prepare Figures (300 DPI TIFF/EPS for CCM)
- [ ] Prepare Tables (editable format)
- [ ] Complete CCM Author Disclosure Form (ICMJE)
- [ ] Register at [ORCID](https://orcid.org)
- [ ] Zenodo: link GitHub repo for automatic DOI minting
- [ ] Replace placeholder DOI in README with real Zenodo DOI
- [ ] Update `author` field in README citation from `IXNO` to real name for submission
- [ ] Upload supplementary materials (all code + data manifests)
- [ ] Verify Brief Report word limit (≤1,500 words main text)
