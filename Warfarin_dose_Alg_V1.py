import streamlit as st
import math
import sqlite3
from datetime import datetime

DB_PATH = "warfarin_patients.db"

# ---------- DB SETUP ----------

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS warfarin_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            age REAL,
            gender INTEGER,
            height_cm REAL,
            weight_kg REAL,
            bmi REAL,
            bsa REAL,
            smoking INTEGER,
            diet_gaikwad INTEGER,
            vitk_pavani INTEGER,
            clinical_condition REAL,
            indication REAL,
            cyp2c9_diplotype TEXT,
            vkor_rs9923231_geno TEXT,
            vkor_rs7294_geno TEXT,
            vkor_rs9934438_geno TEXT,
            vkor_rs2359612_geno TEXT,
            vkor_star4_code INTEGER,
            cyp2c9_star2_code INTEGER,
            cyp2c9_star3_code INTEGER,
            cyp4f2_geno TEXT,
            ggcx_geno TEXT,
            dose_kumar_day REAL,
            dose_pavani_week REAL,
            dose_pavani_day REAL,
            dose_gaikwad_day REAL,
            dose_rathore_day REAL
        )
        """
    )
    conn.commit()
    return conn

conn = init_db()


# ---------- HELPER FUNCTIONS ----------

def calc_bmi(weight_kg: float, height_cm: float) -> float:
    if not weight_kg or not height_cm:
        return None
    h_m = height_cm / 100.0
    if h_m <= 0:
        return None
    return weight_kg / (h_m ** 2)


def calc_bsa_mosteller(weight_kg: float, height_cm: float) -> float:
    if not weight_kg or not height_cm:
        return None
    return math.sqrt((height_cm * weight_kg) / 3600.0)


def geno_to_code(geno: str, wild: str, het: str, hom_var: str) -> int:
    """
    Generic mapping of genotype string -> 0/1/2 numeric code
    e.g. geno_to_code("GA","GG","GA","AA") -> 1
    """
    if geno == wild:
        return 0
    elif geno == het:
        return 1
    elif geno == hom_var:
        return 2
    return 0  # fallback


def cyp2c9_diplotype_to_codes(diplotype: str):
    """
    From CYP2C9 diplotype (*1/*1, *1/*2, etc.) derive:
    - code2: CYP2C9*2 code (0/1/2)
    - code3: CYP2C9*3 code (0/1/2)
    - indicators for Gaikwad model
    """
    dip = diplotype.strip()
    # Counts of *2 and *3 alleles
    count2 = dip.count("*2")
    count3 = dip.count("*3")

    code2 = min(count2, 2)
    code3 = min(count3, 2)

    ind_12 = 1 if dip == "*1/*2" else 0
    ind_13 = 1 if dip == "*1/*3" else 0
    ind_23 = 1 if dip == "*2/*3" else 0
    ind_33 = 1 if dip == "*3/*3" else 0

    return code2, code3, ind_12, ind_13, ind_23, ind_33


def cyp2c9_diplotype_to_snp_genotypes(diplotype: str):
    """
    Approximate mapping from CYP2C9 diplotype -> genotype at:
      - rs1799853 (CYP2C9*2): CC/CT/TT
      - rs1057910 (CYP2C9*3): AA/AC/CC
    This is for Rathore's SNP-style indicators.
    """
    dip = diplotype.strip()
    # Defaults: *1/*1 (wild-type)
    geno_2 = "CC"
    geno_3 = "AA"

    if dip == "*1/*1":
        geno_2, geno_3 = "CC", "AA"
    elif dip == "*1/*2":
        geno_2, geno_3 = "CT", "AA"
    elif dip == "*1/*3":
        geno_2, geno_3 = "CC", "AC"
    elif dip == "*2/*3":
        geno_2, geno_3 = "CT", "AC"
    elif dip == "*3/*3":
        geno_2, geno_3 = "CC", "CC"
    elif dip == "*2/*2":
        geno_2, geno_3 = "TT", "AA"
    else:
        # Fallback, treat as wild
        geno_2, geno_3 = "CC", "AA"

    return geno_2, geno_3


# ---------- MAIN APP UI ----------

st.title("Warfarin Dosing Comparator – 4 Algorithms")
st.markdown(
    """
This app compares *four published warfarin dosing algorithms*:

1. *Kumar et al.* (log10 mg/day, multiple VKORC1/CYP4F2/GGCX SNPs)  
2. *Pavani et al.* (mg/week, CYP2C9 & VKORC1)  
3. *Gaikwad et al.* (√dose mg/day, CYP2C9 diplotype + VKORC1 + diet)  
4. *Rathore et al.* (mg/day, clinical + VKORC1/CYP2C9/CYP4F2/GGCX genotypes)

All inputs are entered *once* and reused across models.  
*BMI and BSA* are calculated automatically.  
Each submission is stored in a local *SQLite database*.
"""
)

with st.form("warfarin_form"):
    st.subheader("Clinical Parameters")

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age (years)", min_value=1, max_value=120, value=50)
        gender = st.selectbox("Gender", options=["Female", "Male"])
        smoking = st.selectbox("Smoking status (Rathore)", options=["Non-smoker", "Smoker"])
        diet_gaikwad = st.selectbox("Diet (Gaikwad: vitamin K intake)", options=["Normal", "High vitamin K"])
        vitk_pavani = st.selectbox("Vitamin K intake (Pavani)", options=["Normal", "High"])
    with col2:
        height_cm = st.number_input("Height (cm)", min_value=100.0, max_value=220.0, value=165.0, step=0.5)
        weight_kg = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=60.0, step=0.5)
        clinical_condition = st.number_input("Clinical condition code (Kumar)", value=0.0,
                                             help="As defined in Kumar et al. (e.g., indication / co-morbidities)")
        indication = st.selectbox(
            "Indication (Rathore)",
            options=["Other / Not DVR/AVR", "DVR", "AVR"],
            help="Rathore: +0.327 for DVR, -0.092 for AVR"
        )

    # Derived BMI & BSA
    bmi = calc_bmi(weight_kg, height_cm)
    bsa = calc_bsa_mosteller(weight_kg, height_cm)

    st.markdown("*Derived values (auto-calculated):*")
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.write(f"*BMI* = {bmi:.2f} kg/m²" if bmi else "BMI = NA")
    with dcol2:
        st.write(f"*BSA (Mosteller)* = {bsa:.2f} m²" if bsa else "BSA = NA")

    st.markdown("---")
    st.subheader("Genetic Parameters")

    st.markdown("##### CYP2C9 diplotype (shared for Gaikwad, Kumar, Pavani, Rathore)")
    cyp2c9_diplotype = st.selectbox(
        "CYP2C9 diplotype",
        options=["*1/*1", "*1/*2", "*1/*3", "*2/*3", "*3/*3", "*2/*2"],
        index=0
    )

    st.markdown("##### VKORC1 SNP genotypes (rs-based)")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        vkor_9923231 = st.selectbox("VKORC1 rs9923231 genotype", ["GG", "GA", "AA"])
        vkor_7294 = st.selectbox("VKORC1 rs7294 genotype", ["CC", "CT", "TT"])
    with col_v2:
        vkor_9934438 = st.selectbox("VKORC1 rs9934438 genotype", ["CC", "CT", "TT"])
        vkor_2359612 = st.selectbox("VKORC1 rs2359612 genotype", ["TT", "TC", "CC"])

    st.markdown("##### VKORC1*4 (Pavani)")
    vkor_star4_code = st.selectbox(
        "VKORC1*4 code (Pavani)",
        options=[0, 1, 2],
        help="0 = no *4; 1 = heterozygous; 2 = homozygous (if known)"
    )

    st.markdown("##### CYP4F2 & GGCX (shared)")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        cyp4f2_geno = st.selectbox("CYP4F2 rs2108622 genotype", ["GG", "GA", "AA"])
    with col_g2:
        ggcx_geno = st.selectbox("GGCX rs11676382 genotype", ["CC", "CG", "GG"])

    st.markdown("##### Rathore-specific genotype strings (auto-derived where possible)")
    st.caption("VKORC1 overall genotype uses rs-based field above (rs9923231 is a proxy). "
               "CYP2C9*2/*3 genotype strings will be derived from the diplotype.")

    # We will use vkor_9923231 as proxy for VKORC1 overall genotype for Rathore:
    vkor_overall_geno = st.selectbox(
        "VKORC1 overall genotype (Rathore)",
        ["GG", "GA", "AA"],
        index=["GG", "GA", "AA"].index(vkor_9923231)
    )

    # Submit button
    submitted = st.form_submit_button("Compute & Save")

if submitted:
    # Map categorical to numeric
    gender_code = 1 if gender == "Male" else 0
    smoking_code = 1 if smoking == "Smoker" else 0
    diet_gaikwad_code = 1 if diet_gaikwad == "High vitamin K" else 0
    vitk_pavani_code = 1 if vitk_pavani == "High" else 0

    if indication == "DVR":
        indication_term = 0.327
    elif indication == "AVR":
        indication_term = -0.092
    else:
        indication_term = 0.0

    # Derived codes from genotypes
    vkor_9923231_code = geno_to_code(vkor_9923231, "GG", "GA", "AA")
    vkor_7294_code = geno_to_code(vkor_7294, "CC", "CT", "TT")
    vkor_9934438_code = geno_to_code(vkor_9934438, "CC", "CT", "TT")
    vkor_2359612_code = geno_to_code(vkor_2359612, "TT", "TC", "CC")
    cyp4f2_code = geno_to_code(cyp4f2_geno, "GG", "GA", "AA")
    ggcx_code = geno_to_code(ggcx_geno, "CC", "CG", "GG")

    # CYP2C9: from diplotype -> codes & Gaikwad indicators
    cyp2_code, cyp3_code, ind_12, ind_13, ind_23, ind_33 = cyp2c9_diplotype_to_codes(cyp2c9_diplotype)
    cyp2_snp_geno, cyp3_snp_geno = cyp2c9_diplotype_to_snp_genotypes(cyp2c9_diplotype)

    # Rathore indicators
    vkor_GA_ind = 1 if vkor_overall_geno == "GA" else 0
    vkor_AA_ind = 1 if vkor_overall_geno == "AA" else 0

    cyp2_CT_ind = 1 if cyp2_snp_geno == "CT" else 0
    cyp3_AC_ind = 1 if cyp3_snp_geno == "AC" else 0

    cyp4f2_GA_ind = 1 if cyp4f2_geno == "GA" else 0
    cyp4f2_AA_ind = 1 if cyp4f2_geno == "AA" else 0

    ggcx_CG_ind = 1 if ggcx_geno == "CG" else 0
    ggcx_GG_ind = 1 if ggcx_geno == "GG" else 0

    # --- Algorithm 1: Kumar et al. (log10 mg/day) ---
    log10_dose_kumar = (
        0.656
        - 0.187 * vkor_9923231_code
        + 0.003 * weight_kg
        - 0.196 * cyp3_code
        - 0.144 * cyp2_code
        + 0.083 * vkor_7294_code
        - 0.003 * age
        + 0.033 * cyp4f2_code
        + 0.037 * clinical_condition
        - 0.074 * vkor_9934438_code
        - 0.097 * vkor_2359612_code
        - 0.130 * ggcx_code
    )
    dose_kumar_day = 10 ** log10_dose_kumar

    # --- Algorithm 2: Pavani et al. (mg/week, then mg/day) ---
    dose_pavani_week = (
        -0.185 * age
        + 8.107 * gender_code
        + 0.139 * (bmi if bmi is not None else 0)
        + 6.698 * cyp2_code
        - 8.276 * cyp3_code
        - 10.727 * vkor_7294_code
        + 8.873 * vkor_star4_code
        + 11.149 * vkor_9923231_code
        - 4.825 * vitk_pavani_code
        + 34.959
    )
    dose_pavani_day = dose_pavani_week / 7.0

    # --- Algorithm 3: Gaikwad et al. (sqrt mg/day) ---
    sqrt_dose_gaikwad = (
        2.61
        - 0.41 * vkor_9923231_code
        - 0.21 * ind_12
        - 0.58 * ind_13
        - 0.86 * ind_23
        - 0.86 * ind_33
        - 0.002 * age
        - 0.08 * diet_gaikwad_code
    )
    # Ensure non-negative before squaring
    sqrt_dose_gaikwad = max(0, sqrt_dose_gaikwad)
    dose_gaikwad_day = sqrt_dose_gaikwad ** 2

    # --- Algorithm 4: Rathore et al. (mg/day) ---
    dose_rathore_day = (
        3.082
        - 0.013 * smoking_code
        - 0.433 * gender_code
        - 0.004 * age
        + indication_term
        + 0.026 * height_cm
        + 0.151 * weight_kg
        - 7.660 * (bsa if bsa is not None else 0)
        - 0.862 * vkor_GA_ind
        - 2.257 * vkor_AA_ind
        - 0.049 * cyp2_CT_ind
        - 0.456 * cyp3_AC_ind
        + 0.449 * cyp4f2_GA_ind
        + 0.230 * cyp4f2_AA_ind
        + 0.245 * ggcx_CG_ind
        + 1.055 * ggcx_GG_ind
    )

    # Safety flags (0.5–10 mg/day)
    def flag(d):
        return "OK" if 0.5 <= d <= 10 else "Check"

    flag_kumar = flag(dose_kumar_day)
    flag_pavani = flag(dose_pavani_day)
    flag_gaikwad = flag(dose_gaikwad_day)
    flag_rathore = flag(dose_rathore_day)

    # Show results
    st.subheader("Dose predictions")
    st.write("Values are *mg/day* unless otherwise specified:")

    st.table({
        "Algorithm": ["Kumar et al.", "Pavani et al.", "Gaikwad et al.", "Rathore et al."],
        "Dose (mg/day)": [
            round(dose_kumar_day, 2),
            round(dose_pavani_day, 2),
            round(dose_gaikwad_day, 2),
            round(dose_rathore_day, 2),
        ],
        "Safety (0.5–10 mg/day)": [flag_kumar, flag_pavani, flag_gaikwad, flag_rathore]
    })

    st.caption(f"Pavani weekly dose estimate: *{dose_pavani_week:.2f} mg/week*")

    # Store in DB
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO warfarin_cases (
            created_at, age, gender, height_cm, weight_kg, bmi, bsa,
            smoking, diet_gaikwad, vitk_pavani, clinical_condition, indication,
            cyp2c9_diplotype, vkor_rs9923231_geno, vkor_rs7294_geno, vkor_rs9934438_geno,
            vkor_rs2359612_geno, vkor_star4_code, cyp2c9_star2_code, cyp2c9_star3_code,
            cyp4f2_geno, ggcx_geno,
            dose_kumar_day, dose_pavani_week, dose_pavani_day, dose_gaikwad_day, dose_rathore_day
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            datetime.utcnow().isoformat(),
            age,
            gender_code,
            height_cm,
            weight_kg,
            bmi,
            bsa,
            smoking_code,
            diet_gaikwad_code,
            vitk_pavani_code,
            clinical_condition,
            indication_term,
            cyp2c9_diplotype,
            vkor_9923231,
            vkor_7294,
            vkor_9934438,
            vkor_2359612,
            vkor_star4_code,
            cyp2_code,
            cyp3_code,
            cyp4f2_geno,
            ggcx_geno,
            dose_kumar_day,
            dose_pavani_week,
            dose_pavani_day,
            dose_gaikwad_day,
            dose_rathore_day
        )
    )
    conn.commit()

    st.success("Results calculated and saved to backend (SQLite).")

    if st.checkbox("Show last 5 saved cases"):
        df_last = None
        import pandas as pd
        df_last = pd.read_sql_query(
            "SELECT * FROM warfarin_cases ORDER BY id DESC LIMIT 5",
            conn
        )
        st.dataframe(df_last)