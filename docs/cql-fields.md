# Officiële Bekendmakingen – SRU/CQL Field Reference

**Endpoint:**
https://repository.overheid.nl/sru

**Query language:** CQL (Contextual Query Language)

---

# 🧠 Core Concept

All queries typically start with:

```
c.product-area == "officielepublicaties"
```

---

# 📦 1. Core System Fields (`c.*`)

| Field            | Description                 | Example                  |
| ---------------- | --------------------------- | ------------------------ |
| `c.product-area` | Dataset selector (required) | `"officielepublicaties"` |

---

# 🏛️ 2. Publication Metadata (`w.*`)

| Field                   | Description            | Example Values                                              |
| ----------------------- | ---------------------- | ----------------------------------------------------------- |
| `w.publicatienaam`      | Type of publication    | `"Staatscourant"`, `"Staatsblad"`, `"Gemeenteblad"`         |
| `w.organisatietype`     | Type of issuing body   | `"ministerie"`, `"gemeente"`, `"provincie"`, `"waterschap"` |
| `w.geografische_naam`   | Municipality or region | `"Amsterdam"`                                               |
| `w.identificatienummer` | Unique publication ID  | `"stcrt-2024-12345"`                                        |

---

# 🧾 3. Dublin Core Fields (`dc.*`)

| Field            | Description             | Example                           |
| ---------------- | ----------------------- | --------------------------------- |
| `dc.title`       | Title of document       | `"Regeling verkeersmaatregelen"`  |
| `dc.creator`     | Authoring organization  | `"Ministerie van Infrastructuur"` |
| `dc.identifier`  | Unique identifier (URI) | `"https://..."`                   |
| `dc.subject`     | Topic/category          | `"verkeer"`                       |
| `dc.description` | Summary/description     | `"Besluit tot..."`                |
| `dc.type`        | Document type           | `"regeling"`                      |
| `dc.language`    | Language                | `"nl"`                            |

---

# 🏷️ 4. Extended Metadata (`dcterms.*`)

| Field              | Description      | Example                   |
| ------------------ | ---------------- | ------------------------- |
| `dcterms.date`     | Publication date | `"2024-01-15"`            |
| `dcterms.modified` | Last modified    | `"2024-01-16"`            |
| `dcterms.valid`    | Validity period  | `"2024-01-01/2025-01-01"` |
| `dcterms.spatial`  | Geographic scope | `"Nederland"`             |

---

# 🧑‍⚖️ 5. Domain-Specific Fields (`dt.*`)

These are heavily used in the UI filters.

| Field           | Description                                 | Example                             |
| --------------- | ------------------------------------------- | ----------------------------------- |
| `dt.creator`    | Organization (more precise than dc.creator) | `"Ministerie van Financiën"`        |
| `dt.subject`    | Policy topic                                | `"wonen"`, `"energie"`, `"verkeer"` |
| `dt.type`       | Specific document subtype                   | `"beleidsregel"`                    |
| `dt.identifier` | Internal ID                                 | varies                              |

---

# 📍 6. Geographic Fields

| Field                 | Description         | Example          |
| --------------------- | ------------------- | ---------------- |
| `w.geografische_naam` | Municipality/region | `"Rotterdam"`    |
| `dcterms.spatial`     | Broader geography   | `"Zuid-Holland"` |

---

# 📅 7. Date Filtering

| Field          | Description      | Example        |
| -------------- | ---------------- | -------------- |
| `dcterms.date` | Publication date | `"2024-01-01"` |

### Range query:

```
dcterms.date >= "2024-01-01" AND dcterms.date <= "2024-01-31"
```

---

# 🔎 8. Text Search Fields

| Field            | Description     | Notes                  |
| ---------------- | --------------- | ---------------------- |
| `dc.title`       | Title search    | exact or fuzzy         |
| `dc.description` | Content summary | useful for keywords    |
| `dt.subject`     | Topic search    | cleaner than free text |

---

# ⚙️ Operators

| Operator | Meaning               | Example                               |
| -------- | --------------------- | ------------------------------------- |
| `==`     | equals                | `w.publicatienaam == "Staatscourant"` |
| `AND`    | logical AND           | `A AND B`                             |
| `OR`     | logical OR            | `A OR B`                              |
| `>=`     | greater than or equal | date filtering                        |
| `<=`     | less than or equal    | date filtering                        |

---

# 🧪 Example Queries

## 1. All official publications

```
c.product-area == "officielepublicaties"
```

---

## 2. Staatscourant only

```
c.product-area == "officielepublicaties"
AND w.publicatienaam == "Staatscourant"
```

---

## 3. Municipality-specific (Amsterdam)

```
c.product-area == "officielepublicaties"
AND w.geografische_naam == "Amsterdam"
```

---

## 4. Topic filter (housing)

```
c.product-area == "officielepublicaties"
AND dt.subject == "wonen"
```

---

## 5. Ministry + topic + type

```
c.product-area == "officielepublicaties"
AND w.organisatietype == "ministerie"
AND dt.subject == "energie"
AND w.publicatienaam == "Staatscourant"
```

---

## 6. Date range

```
c.product-area == "officielepublicaties"
AND dcterms.date >= "2024-01-01"
AND dcterms.date <= "2024-01-31"
```

---

# ⚠️ Known Limitations

* Field availability is inconsistent across documents
* Some records miss `dt.*` fields
* XML structure varies slightly per publication type
* No official schema documentation exists

---

# 💡 Practical Recommendations

Start with these fields only:

* `w.publicatienaam`
* `dcterms.date`
* `dt.subject`
* `dt.creator`
* `w.geografische_naam`

These cover ~80% of useful filtering.

---

# 🧭 Mental Model

This is not a structured API.

It is:

> a searchable metadata index exposed via a library protocol (SRU + CQL)

---

# ✅ MVP Query Template

```
c.product-area == "officielepublicaties"
AND dcterms.date >= "{from_date}"
AND dcterms.date <= "{to_date}"
```

---

# End of Reference
