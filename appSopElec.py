# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 18:08:47 2025

@author: acer
"""


import streamlit as st
import pandas as pd
import io

# Configuración de página para mejor visualización
st.set_page_config(layout="wide")
st.title("📁 Consolidador de CSV de Máquina (por fecha y análisis)")

uploaded_files = st.file_uploader(
    "Arrastra aquí tus CSV",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    dfs = []

    COLUMNA_FECHA_ORIGEN = "FECHA Y HORA"

    # ⚠️ NOTA: Si no convertimos 'FECHA Y HORA' a datetime,
    # la columna 'FECHA Y HORA' no se podrá usar para ordenar.
    # Usaremos una columna temporal para ordenar internamente.

    for file in uploaded_files:
        try:
            # Leemos el CSV especificando que el encabezado es la tercera fila (índice 2).
            df = pd.read_csv(file, header=2, encoding="latin1")

            # Normalizar nombres de columnas (eliminar espacios)
            df.columns = df.columns.str.strip()

            # --- PRE-PROCESAMIENTO PARA ORDENAR Y CALCULAR ---

            # Columna Temporal de Fecha para poder Ordenar
            if COLUMNA_FECHA_ORIGEN in df.columns:
                df["_FECHA_TEMPORAL_"] = pd.to_datetime(
                    df[COLUMNA_FECHA_ORIGEN],
                    format="%m-%d-%H:%M:%S",
                    errors="coerce"
                )

            # Convertir columnas clave a numérico antes de consolidar
            cols_to_numeric = ["VALOR_FUGA", "EXPONENCIAL", "ESTADO", "CALIBRACION", "DUMMY TEST", "FUGA CALIBRADA"]
            for col in cols_to_numeric:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            dfs.append(df)

        except Exception as e:
            st.error(f"❌ Error procesando {file.name}: {e}")

    if dfs:
        # Unir todos los DataFrames
        df_final = pd.concat(dfs, ignore_index=True)

        # Ordenar por la columna temporal (que sí tiene formato de fecha)
        if "_FECHA_TEMPORAL_" in df_final.columns:
            df_final = df_final.sort_values(by="_FECHA_TEMPORAL_")
            # Eliminamos la columna temporal después de ordenar
            df_final = df_final.drop(columns=["_FECHA_TEMPORAL_"])


        # --- TAREAS DE TRANSFORMACIÓN SOLICITADAS ---

        ### 1) Copiar FECHA Y HORA directamente a TIME (Sin formatear/convertir)
        if COLUMNA_FECHA_ORIGEN in df_final.columns:
            # Copia directa como string. Esto evita el problema del año 1900.
            df_final["TIME"] = df_final[COLUMNA_FECHA_ORIGEN]
            st.success("✅ Punto 1: Columna 'TIME' copiada directamente desde 'FECHA Y HORA' (sin formato).")

        ### 3) Aplicar fórmula a la columna 'DECIMAL'
        required_cols_calc = ["VALOR_FUGA", "EXPONENCIAL"]
        if all(col in df_final.columns for col in required_cols_calc):
            # Solución: Usamos 10.0 en lugar de 10 para evitar el error de potencias negativas.
            df_final["DECIMAL"] = df_final["VALOR_FUGA"] * (10.0 ** df_final["EXPONENCIAL"])
            st.success("✅ Punto 3: Cálculo de la columna 'DECIMAL' aplicado.")
        else:
            st.error("❌ Error: Faltan las columnas VALOR_FUGA o EXPONENCIAL.")

        # --- VISTA PREVIA Y DESCARGA ---

        st.write("---")
        st.subheader("📊 Datos Consolidados y Transformados (Vista Previa)")
        st.dataframe(df_final.head(10), use_container_width=True)

        # Generar Excel con Formato Condicional (Punto 2)
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_final.to_excel(writer, index=False, sheet_name="Consolidado")

                workbook = writer.book
                worksheet = writer.sheets["Consolidado"]

                # Definir formatos de color
                format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

                # Columnas a aplicar formato condicional (Punto 2)
                columns_to_format = ["ESTADO", "CALIBRACION", "DUMMY TEST", "FUGA CALIBRADA"]

                for col_name in columns_to_format:
                    if col_name in df_final.columns:
                        col_idx = df_final.columns.get_loc(col_name)
                        col_letter = chr(65 + col_idx)
                        max_row = len(df_final) + 1

                        # Formato condicional: Si es 1 (Verde)
                        worksheet.conditional_format(
                            f'{col_letter}2:{col_letter}{max_row}',
                            {'type': 'cell', 'criteria': '==', 'value': 1, 'format': format_green}
                        )

                        # Formato condicional: Si es 2 (Rojo)
                        worksheet.conditional_format(
                            f'{col_letter}2:{col_letter}{max_row}',
                            {'type': 'cell', 'criteria': '==', 'value': 2, 'format': format_red}
                        )
                st.info("🎨 Punto 2: Formato condicional aplicado en el Excel de descarga.")

        except Exception as e:
            st.error(f"❌ Error al generar el Excel con formato condicional. Se generará un Excel simple: {e}")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_final.to_excel(writer, index=False, sheet_name="Consolidado")


        st.download_button(
            label="📥 Descargar Excel Consolidado con Análisis",
            data=buffer,
            file_name="datos_consolidados_analisis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
