import json

from backend.database import SessionLocal
from backend.models.biomarker import BiomarkerReference


BIOMARKERS = [
    {"name": "White Blood Cells", "category": "Complete Blood Count", "aliases": ["WBC", "WHITE BLOOD CELL"]},
    {"name": "Red Blood Cells", "category": "Complete Blood Count", "aliases": ["RBC", "RED BLOOD CELL"]},
    {"name": "Hemoglobin", "category": "Complete Blood Count", "aliases": ["HGB", "HEMOGLOBIN"]},
    {"name": "Hematocrit", "category": "Complete Blood Count", "aliases": ["HCT", "HEMATOCRIT"]},
    {"name": "Mean Corpuscular Volume", "category": "Complete Blood Count", "aliases": ["MCV"]},
    {"name": "Platelets", "category": "Complete Blood Count", "aliases": ["PLT", "PLATELET"]},
    {"name": "Glucose", "category": "Metabolic Panel", "aliases": ["GLUCOSE", "FASTING GLUCOSE"]},
    {"name": "Sodium", "category": "Electrolytes", "aliases": ["NA", "SODIUM"]},
    {"name": "Potassium", "category": "Electrolytes", "aliases": ["K", "POTASSIUM"]},
    {"name": "Chloride", "category": "Electrolytes", "aliases": ["CL", "CHLORIDE"]},
    {"name": "Creatinine", "category": "Kidney Function", "aliases": ["CREATININE", "CREAT"]},
    {"name": "Blood Urea Nitrogen", "category": "Kidney Function", "aliases": ["BUN", "UREA NITROGEN"]},
    {"name": "Calcium", "category": "Metabolic Panel", "aliases": ["CALCIUM"]},
    {"name": "Magnesium", "category": "Electrolytes", "aliases": ["MAGNESIUM"]},
    {"name": "Total Protein", "category": "Protein", "aliases": ["TOTAL PROTEIN"]},
    {"name": "Albumin", "category": "Protein", "aliases": ["ALBUMIN"]},
    {"name": "Globulin", "category": "Protein", "aliases": ["GLOBULIN"]},
    {"name": "AST", "category": "Liver Function", "aliases": ["AST", "SGOT", "TRANSAMINASE-SGO"]},
    {"name": "ALT", "category": "Liver Function", "aliases": ["ALT", "SGPT"]},
    {"name": "Alkaline Phosphatase", "category": "Liver Function", "aliases": ["ALP", "ALKALINE PHOSPHATASE"]},
    {"name": "GGT", "category": "Liver Function", "aliases": ["GAMMA GLUT. TRANSPEPTIDASE", "GGT"]},
    {"name": "Total Bilirubin", "category": "Liver Function", "aliases": ["TOTAL BILIRUBIN", "BILIRUBIN"]},
    {"name": "Direct Bilirubin", "category": "Liver Function", "aliases": ["DIRECT BILIRUBIN"]},
    {"name": "Total Cholesterol", "category": "Lipid Panel", "aliases": ["CHOLESTEROL", "TOTAL CHOLESTEROL"]},
    {"name": "LDL Cholesterol", "category": "Lipid Panel", "aliases": ["LDL", "LDL-CALCULATED"]},
    {"name": "HDL Cholesterol", "category": "Lipid Panel", "aliases": ["HDL", "HIGH DENSITY LIPOPROTEIN"]},
    {"name": "Triglycerides", "category": "Lipid Panel", "aliases": ["TRIGLYCERIDES", "TG"]},
    {"name": "TSH", "category": "Thyroid", "aliases": ["TSH", "THYROID STIMULATING HORMONE"]},
    {"name": "HbA1c", "category": "Diabetes", "aliases": ["A1C", "HBA1C", "HEMOGLOBIN A1C"]},
    {"name": "Ferritin", "category": "Iron Studies", "aliases": ["FERRITIN"]},
    {"name": "Vitamin D", "category": "Vitamins", "aliases": ["25-OH VITAMIN D", "VITAMIN D"]},
    {"name": "Vitamin B12", "category": "Vitamins", "aliases": ["B12", "VITAMIN B12"]},
    {"name": "C-Reactive Protein", "category": "Inflammation", "aliases": ["CRP", "C-REACTIVE PROTEIN"]},
    {"name": "Mean Corpuscular Hemoglobin", "category": "Complete Blood Count", "aliases": ["MCH"]},
    {"name": "Mean Corpuscular Hemoglobin Concentration", "category": "Complete Blood Count", "aliases": ["MCHC"]},
    {"name": "Red Cell Distribution Width", "category": "Complete Blood Count", "aliases": ["RDW"]},
    {"name": "Mean Platelet Volume", "category": "Complete Blood Count", "aliases": ["MPV"]},
    {"name": "Neutrophils Percent", "category": "Differential Count", "aliases": ["NEUTROPHILS", "POLY (PERCENT)"]},
    {"name": "Lymphocytes Percent", "category": "Differential Count", "aliases": ["LYMPH (PERCENT)", "LYMPHOCYTES"]},
    {"name": "Monocytes Percent", "category": "Differential Count", "aliases": ["MONO (PERCENT)", "MONOCYTES"]},
    {"name": "Eosinophils Percent", "category": "Differential Count", "aliases": ["EOS (PERCENT)", "EOSINOPHILS"]},
    {"name": "Basophils Percent", "category": "Differential Count", "aliases": ["BASO (PERCENT)", "BASOPHILS"]},
    {"name": "Absolute Neutrophil Count", "category": "Differential Count", "aliases": ["ABS POLY COUNT", "ANC"]},
    {"name": "Absolute Lymphocyte Count", "category": "Differential Count", "aliases": ["ABS LYMPH COUNT"]},
    {"name": "Absolute Monocyte Count", "category": "Differential Count", "aliases": ["ABS MONO COUNT"]},
    {"name": "Absolute Eosinophil Count", "category": "Differential Count", "aliases": ["ABS EOS COUNT"]},
    {"name": "Absolute Basophil Count", "category": "Differential Count", "aliases": ["ABS BASO COUNT"]},
    {"name": "Carbon Dioxide", "category": "Metabolic Panel", "aliases": ["CO2", "CARBON DIOXIDE", "BICARBONATE"]},
    {"name": "Uric Acid", "category": "Kidney Function", "aliases": ["URIC ACID"]},
    {"name": "Phosphorus", "category": "Electrolytes", "aliases": ["PHOSPHORUS", "INORGANIC PHOSPHATE"]},
    {"name": "Albumin Globulin Ratio", "category": "Protein", "aliases": ["ALBUMIN/GLOBULIN RATIO", "A/G RATIO"]},
    {"name": "Lactate Dehydrogenase", "category": "Cardiac Markers", "aliases": ["LDH", "LACTATE DEHYDROGENASE"]},
    {"name": "Iron", "category": "Iron Studies", "aliases": ["IRON", "SERUM IRON"]},
    {"name": "Cholesterol Percentile", "category": "Lipid Panel", "aliases": ["CHOLESTEROL PERCENTILE"]},
    {"name": "HDL Cholesterol Percent", "category": "Lipid Panel", "aliases": ["HDL/CHOLESTEROL PERCENT"]},
    {"name": "Apolipoprotein B", "category": "Lipid Panel", "aliases": ["APOB", "APOLIPOPROTEIN B"]},
    {"name": "Lipoprotein(a)", "category": "Lipid Panel", "aliases": ["LPA", "LIPOPROTEIN(A)"]},
    {"name": "Non HDL Cholesterol", "category": "Lipid Panel", "aliases": ["NON HDL CHOLESTEROL"]},
    {"name": "Free T3", "category": "Thyroid", "aliases": ["FT3", "FREE T3"]},
    {"name": "Free T4", "category": "Thyroid", "aliases": ["FT4", "FREE T4"]},
    {"name": "Total T3", "category": "Thyroid", "aliases": ["TOTAL T3"]},
    {"name": "Total T4", "category": "Thyroid", "aliases": ["TOTAL T4"]},
    {"name": "Thyroid Peroxidase Antibody", "category": "Thyroid", "aliases": ["TPO AB", "TPO ANTIBODY"]},
    {"name": "Thyroglobulin Antibody", "category": "Thyroid", "aliases": ["TG AB", "THYROGLOBULIN AB"]},
    {"name": "Insulin", "category": "Diabetes", "aliases": ["FASTING INSULIN", "INSULIN"]},
    {"name": "HOMA IR", "category": "Diabetes", "aliases": ["HOMA-IR", "HOMA IR"]},
    {"name": "Fructosamine", "category": "Diabetes", "aliases": ["FRUCTOSAMINE"]},
    {"name": "eGFR", "category": "Kidney Function", "aliases": ["EGFR", "ESTIMATED GFR"]},
    {"name": "Cystatin C", "category": "Kidney Function", "aliases": ["CYSTATIN C"]},
    {"name": "BUN Creatinine Ratio", "category": "Kidney Function", "aliases": ["BUN/CREATININE RATIO"]},
    {"name": "Urine Albumin", "category": "Kidney Function", "aliases": ["MICROALBUMIN", "URINE ALBUMIN"]},
    {"name": "Urine Creatinine", "category": "Kidney Function", "aliases": ["URINE CREATININE"]},
    {"name": "Albumin Creatinine Ratio", "category": "Kidney Function", "aliases": ["ACR", "ALBUMIN CREATININE RATIO"]},
    {"name": "Gamma Glutamyl Transferase", "category": "Liver Function", "aliases": ["GAMMA GLUTAMYL TRANSFERASE", "GGT"]},
    {"name": "Bilirubin Indirect", "category": "Liver Function", "aliases": ["INDIRECT BILIRUBIN"]},
    {"name": "Prothrombin Time", "category": "Coagulation", "aliases": ["PT", "PROTHROMBIN TIME"]},
    {"name": "INR", "category": "Coagulation", "aliases": ["INR"]},
    {"name": "Activated Partial Thromboplastin Time", "category": "Coagulation", "aliases": ["APTT", "PTT"]},
    {"name": "Fibrinogen", "category": "Coagulation", "aliases": ["FIBRINOGEN"]},
    {"name": "D-Dimer", "category": "Coagulation", "aliases": ["D DIMER", "D-DIMER"]},
    {"name": "Estradiol", "category": "Hormones", "aliases": ["E2", "ESTRADIOL"]},
    {"name": "Progesterone", "category": "Hormones", "aliases": ["PROGESTERONE"]},
    {"name": "Testosterone Total", "category": "Hormones", "aliases": ["TOTAL TESTOSTERONE", "TESTOSTERONE"]},
    {"name": "Testosterone Free", "category": "Hormones", "aliases": ["FREE TESTOSTERONE"]},
    {"name": "DHEA Sulfate", "category": "Hormones", "aliases": ["DHEA-S", "DHEA SULFATE"]},
    {"name": "Cortisol", "category": "Hormones", "aliases": ["CORTISOL"]},
    {"name": "Sex Hormone Binding Globulin", "category": "Hormones", "aliases": ["SHBG"]},
    {"name": "Luteinizing Hormone", "category": "Hormones", "aliases": ["LH", "LUTEINIZING HORMONE"]},
    {"name": "Follicle Stimulating Hormone", "category": "Hormones", "aliases": ["FSH", "FOLLICLE STIMULATING HORMONE"]},
    {"name": "Prolactin", "category": "Hormones", "aliases": ["PROLACTIN"]},
    {"name": "Parathyroid Hormone", "category": "Hormones", "aliases": ["PTH", "PARATHYROID HORMONE"]},
    {"name": "Vitamin A", "category": "Vitamins", "aliases": ["VITAMIN A", "RETINOL"]},
    {"name": "Vitamin E", "category": "Vitamins", "aliases": ["VITAMIN E", "TOCOPHEROL"]},
    {"name": "Folate", "category": "Vitamins", "aliases": ["FOLATE", "FOLIC ACID"]},
    {"name": "Homocysteine", "category": "Inflammation", "aliases": ["HOMOCYSTEINE"]},
    {"name": "Erythrocyte Sedimentation Rate", "category": "Inflammation", "aliases": ["ESR", "SED RATE"]},
    {"name": "High Sensitivity CRP", "category": "Inflammation", "aliases": ["HS-CRP", "HIGH SENSITIVITY CRP"]},
    {"name": "Troponin I", "category": "Cardiac Markers", "aliases": ["TROPONIN I"]},
    {"name": "Troponin T", "category": "Cardiac Markers", "aliases": ["TROPONIN T"]},
    {"name": "BNP", "category": "Cardiac Markers", "aliases": ["B-TYPE NATRIURETIC PEPTIDE", "BNP"]},
    {"name": "NT-proBNP", "category": "Cardiac Markers", "aliases": ["NTPROBNP", "NT-PROBNP"]},
    {"name": "Creatine Kinase", "category": "Cardiac Markers", "aliases": ["CK", "CPK"]},
    {"name": "Creatine Kinase MB", "category": "Cardiac Markers", "aliases": ["CK-MB"]},
    {"name": "Sodium Urine", "category": "Urinalysis", "aliases": ["URINE SODIUM"]},
    {"name": "Potassium Urine", "category": "Urinalysis", "aliases": ["URINE POTASSIUM"]},
    {"name": "Urine pH", "category": "Urinalysis", "aliases": ["URINE PH"]},
    {"name": "Urine Specific Gravity", "category": "Urinalysis", "aliases": ["SPECIFIC GRAVITY"]},
    {"name": "Urine Protein", "category": "Urinalysis", "aliases": ["URINE PROTEIN", "PROTEIN URINE"]},
    {"name": "Urine Glucose", "category": "Urinalysis", "aliases": ["URINE GLUCOSE"]},
    {"name": "Urine Ketones", "category": "Urinalysis", "aliases": ["URINE KETONES", "KETONES"]},
    {"name": "Urine Blood", "category": "Urinalysis", "aliases": ["URINE BLOOD", "HEMATURIA"]},
    {"name": "Urine Leukocyte Esterase", "category": "Urinalysis", "aliases": ["LEUKOCYTE ESTERASE"]},
    {"name": "Urine Nitrites", "category": "Urinalysis", "aliases": ["NITRITE", "NITRITES"]},
    {"name": "Transferrin", "category": "Iron Studies", "aliases": ["TRANSFERRIN"]},
    {"name": "Total Iron Binding Capacity", "category": "Iron Studies", "aliases": ["TIBC", "TOTAL IRON BINDING CAPACITY"]},
    {"name": "Transferrin Saturation", "category": "Iron Studies", "aliases": ["TRANSFERRIN SATURATION", "IRON SATURATION"]},
    {"name": "Unsaturated Iron Binding Capacity", "category": "Iron Studies", "aliases": ["UIBC", "UNSATURATED IRON BINDING CAPACITY"]},
]


def seed_biomarkers():
    db = SessionLocal()
    try:
        existing = {
            row.standard_name: row
            for row in db.query(BiomarkerReference).all()
        }
        for item in BIOMARKERS:
            match = existing.get(item["name"])
            if match:
                match.category = item["category"]
                match.common_aliases = json.dumps(item["aliases"])
                db.add(match)
                continue

            db.add(
                BiomarkerReference(
                    standard_name=item["name"],
                    category=item["category"],
                    description=None,
                    common_aliases=json.dumps(item["aliases"]),
                )
            )
        db.commit()
    finally:
        db.close()
