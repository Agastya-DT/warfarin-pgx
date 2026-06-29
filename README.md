# warfarin-pgx — Personalized Blood-Thinner Dosing

## What is this, in plain English?

Warfarin is a common **blood-thinning medicine**. Getting the dose right is tricky: too much and a person can bleed dangerously, too little and they can form harmful clots. The "right" amount is different for every person — it depends on things like their age, weight, lifestyle, and even their **genes**.

This project is a small **calculator app** that helps estimate a sensible starting dose of warfarin for a specific person, instead of using a one-size-fits-all number.

## How does it work?

You enter a patient's details, and the app does the math for you:

- **Basic information** — age, gender, height, and weight
- **Lifestyle** — things like smoking and diet
- **Genetic information** — specific gene variants (such as *CYP2C9* and *VKORC1*) that affect how quickly a body processes warfarin

The app then combines all of this and suggests a personalized dose. Each calculation can be **saved**, so a record of past cases is kept.

## Why genes matter here

Two people of the same age and weight can need very different doses purely because of their genetics. Some people break warfarin down slowly and need much less; others clear it quickly and need more. Taking genetics into account is part of what's called **"precision medicine"** — tailoring treatment to the individual.

## What's inside this project

| File | What it is |
|------|-----------|
| `Warfarin_dose_Alg_V1.py` | The app itself — a web calculator built with Python and Streamlit. |
| `Warfarin_4_Algorithm_Comparator.xlsx` | A spreadsheet that compares results from different dosing methods. |
| `warfarin_patients.db` | A small database that stores saved patient calculations. |

## How to run it

This is a Python app built with **Streamlit**. Once Python and Streamlit are installed, you can launch it with:

```
streamlit run Warfarin_dose_Alg_V1.py
```

A web page will open in your browser where you can enter details and see the suggested dose.

---

> ⚠️ **Important:** This is a **research and learning project**. It is **not** a medical product and must **not** be used to make real decisions about anyone's medication. Always rely on qualified healthcare professionals for actual treatment.
