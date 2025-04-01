import streamlit as st
import pandas as pd
import io

st.title("Monatliche Ausbeuteanalyse")

# === Schritt 1: Referenztabelle hochladen ===
st.subheader("Schritt 1: Referenztabelle hochladen")
dimension_file = st.file_uploader(
    "Bitte lade die Excel-Datei mit der Referenztabelle hoch (zwei Spalten: z. B. 'Dim1' und 'Dim2')",
    type=["xlsx", "xls"]
)

# === Schritt 2: Tages-Excel-Dateien hochladen ===
st.subheader("Schritt 2: Tages-Excel-Dateien eines Monats hochladen")
daily_files = st.file_uploader(
    "Wähle mehrere Tagesdateien aus (alle haben dasselbe Format)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

# Button, um die Verarbeitung zu starten
if st.button("Auswertung starten"):
    if dimension_file is None:
        st.warning("Bitte zuerst die Referenztabelle hochladen.")
        st.stop()
    if not daily_files:
        st.warning("Bitte mindestens eine Tagesdatei hochladen.")
        st.stop()

    # === Referenztabelle einlesen und verarbeiten ===
    try:
        ref_df = pd.read_excel(dimension_file)
    except Exception as e:
        st.error(f"Fehler beim Einlesen der Referenztabelle: {e}")
        st.stop()

    # Annahme: Die Referenztabelle hat zwei Spalten (z.B. erste Spalte: Dim1, zweite: Dim2) im Format "75,00"
    # Wir wandeln beide Spalten in einen einheitlichen Schlüssel "75x75" um.
    ref_df["Dim1"] = (
        ref_df.iloc[:, 0]
        .astype(str)
        .str.replace(",", ".")
        .astype(float)
        .astype(int)
        .astype(str)
    )
    ref_df["Dim2"] = (
        ref_df.iloc[:, 1]
        .astype(str)
        .str.replace(",", ".")
        .astype(float)
        .astype(int)
        .astype(str)
    )
    ref_df["DimensionKey"] = ref_df["Dim1"] + "x" + ref_df["Dim2"]
    # Optional: Falls Du einen SortIndex benötigst, kannst Du diesen in der Referenztabelle hinzufügen.
    # Falls die Tabelle bereits in der gewünschten Reihenfolge vorliegt, kannst Du einen automatisch generieren:
    ref_df.reset_index(inplace=True)
    ref_df.rename(columns={"index": "SortIndex"}, inplace=True)
    # Wir erhöhen den SortIndex um 1, falls gewünscht
    ref_df["SortIndex"] = ref_df["SortIndex"] + 1

    # === Tagesdaten einlesen und zusammenführen ===
    all_dfs = []
    for f in daily_files:
        try:
            df_temp = pd.read_excel(f)
            all_dfs.append(df_temp)
        except Exception as e:
            st.error(f"Fehler beim Einlesen der Datei {f.name}: {e}")

    if not all_dfs:
        st.warning("Es konnten keine Tagesdateien eingelesen werden.")
        st.stop()

    daily_df = pd.concat(all_dfs, ignore_index=True)

    # === Anpassung der Tagesdaten ===
    # Wir nehmen an, dass in den Tagesdaten bereits eine Spalte "Dimension" existiert.
    # Falls nicht, passe diesen Schritt an.
    daily_df["Dimension"] = daily_df["Dimension"].astype(str).str.strip()
    # Falls Du auch in den Tagesdaten das Format angleichen musst (z. B. "75,00" -> "75x75"), dann:
    # Wir nehmen an, dass in den Tagesdateien "Dimension" bereits im richtigen Format steht.
    # Falls nicht, kannst Du z.B.:
    # daily_df["Dim1"] = daily_df["Dimension"].str.split("x").str[0].str.replace(",", ".").astype(float).astype(int).astype(str)
    # daily_df["Dim2"] = daily_df["Dimension"].str.split("x").str[1].str.replace(",", ".").astype(float).astype(int).astype(str)
    # daily_df["DimensionKey"] = daily_df["Dim1"] + "x" + daily_df["Dim2"]
    # Für dieses Beispiel gehen wir davon aus, dass daily_df["Dimension"] schon den Key liefert:
    daily_df["DimensionKey"] = daily_df["Dimension"]

    # === Aggregation der Tagesdaten ===
    # Wir aggregieren anhand des "DimensionKey". Passe die Spaltennamen an Dein konkretes Format an.
    agg_df = daily_df.groupby("DimensionKey", as_index=False).agg({
        "Volumen_Ausgang": "sum",
        "Brutto_Volumen": "sum",
        "Brutto_Ausschuss": "sum",
        "Netto_Volumen": "sum",
        "Brutto_Ausbeute": "sum",
        "Netto_Ausbeute": "sum",
        "CE": "sum",
        "SF": "sum",
        "SI": "sum",
        "IND": "sum",
        "NSI": "sum",
        "Q_V": "sum",
        "Ausschuss": "sum"
    })

    # === Left Join: Alle Dimensionen aus der Referenztabelle übernehmen ===
    final_df = pd.merge(
        ref_df,       # linke Tabelle: enthält alle Dimensionen mit SortIndex
        agg_df,       # rechte Tabelle: aggregierte Tagesdaten
        on="DimensionKey",
        how="left"
    )

    # Ersetze NaN-Werte in den numerischen Kennzahl-Spalten durch 0
    numeric_cols = [
        "Volumen_Ausgang", "Brutto_Volumen", "Brutto_Ausschuss",
        "Netto_Volumen", "Brutto_Ausbeute", "Netto_Ausbeute",
        "CE", "SF", "SI", "IND", "NSI", "Q_V", "Ausschuss"
    ]
    for col in numeric_cols:
        if col in final_df.columns:
            final_df[col] = final_df[col].fillna(0)

    # Sortiere nach SortIndex
    final_df.sort_values("SortIndex", inplace=True)

    # === Ergebnis anzeigen ===
    st.subheader("Ergebnis-Tabelle")
    st.dataframe(final_df)

    # === Excel-Export vorbereiten ===
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        final_df.to_excel(writer, index=False, sheet_name="Ergebnis")
    output.seek(0)

    st.download_button(
        label="Ergebnis als Excel herunterladen",
        data=output,
        file_name="Ausbeuteanalyse_Ergebnis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
