import pandas as pd
import numpy as np
import os
import glob
import zipfile

# --- CONFIGURACIÓN DE RUTAS ---
BASE_PATH = r"C:\Users\Harvy\Downloads\Dataset 2020  - 2025"
OUTPUT_DIR = r"C:\Users\Harvy\Downloads\Proyecto_Desempleo_Pasto\04_Dataset_Procesado"

os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'Pasto_dataset_consolidado.csv')
LOG_PATH = os.path.join(OUTPUT_DIR, 'log_limpieza.csv')

registro_limpieza = []
todos_los_dataframes = []

# Función para leer DataFrames y filtrar Pasto
def procesar_dataframe(df, nombre_archivo):
    if df is None or 'DPTO' not in df.columns:
        return None
        
    registros_antes = len(df)
    
    # Filtro por departamento (Nariño = 52)
    df['DPTO'] = pd.to_numeric(df['DPTO'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
    df_pasto = df[df['DPTO'] == '52'].copy()
    registros_filtrados = len(df_pasto)
    
    if registros_filtrados == 0:
        return None
        
    # Eliminar duplicados
    df_pasto = df_pasto.drop_duplicates()
    registros_finales = len(df_pasto)
    
    # Columnas de interés
    columnas_interes = [
        'DIRECTORIO', 'SECUENCIA_P', 'ORDEN', 'HOGAR', 'DPTO', 'AREA', 'CLASE',
        'P3271', 'P6040', 'P3042', 'OCI', 'DSI', 'FT', 'RAMA2D_R4', 'P6430', 'INGLABO', 'P6800',
        'PERIODO', 'MES', 'PER'
    ]
    columnas_presentes = [col for col in columnas_interes if col in df_pasto.columns]
    
    if not columnas_presentes:
        return None
        
    df_final = df_pasto[columnas_presentes].copy()
    df_final['archivo_origen'] = nombre_archivo
    
    # Guardar en log
    registro_limpieza.append({
        'archivo': nombre_archivo,
        'registros_originales': registros_antes,
        'registros_filtrados_pasto': registros_filtrados,
        'registros_finales_sin_duplicados': registros_finales
    })
    
    return df_final

# --- BUSCAR ARCHIVOS ---
print(f"Buscando archivos en: {BASE_PATH}...")
archivos = glob.glob(os.path.join(BASE_PATH, '**', '*.*'), recursive=True)
# Filtrar solo los que nos interesan
archivos_validos = [f for f in archivos if f.lower().endswith(('.zip', '.csv', '.txt', '.xlsx'))]

print(f"Se encontraron {len(archivos_validos)} archivos candidatos para procesar.\n")

for i, archivo in enumerate(archivos_validos):
    nombre_base = os.path.basename(archivo)
    print(f"[{i+1}/{len(archivos_validos)}] Procesando: {nombre_base}")
    
    try:
        # CASO 1: Es un archivo ZIP
        if archivo.lower().endswith('.zip'):
            with zipfile.ZipFile(archivo, 'r') as z:
                for file_info in z.infolist():
                    if file_info.is_dir() or not file_info.filename.lower().endswith(('.csv', '.txt')):
                        continue
                    with z.open(file_info.filename) as f:
                        df = None
                        for sep in [',', ';', '|', '\t']:
                            for enc in ['latin-1', 'utf-8']:
                                try:
                                    f.seek(0)
                                    df_temp = pd.read_csv(f, low_memory=False, sep=sep, encoding=enc, on_bad_lines='skip')
                                    if 'DPTO' in df_temp.columns:
                                        df = df_temp
                                        break
                                except:
                                    continue
                            if df is not None:
                                break
                        
                        df_procesado = procesar_dataframe(df, f"{nombre_base}|{file_info.filename}")
                        if df_procesado is not None:
                            todos_los_dataframes.append(df_procesado)
        
        # CASO 2: Es Excel
        elif archivo.lower().endswith('.xlsx'):
            df = pd.read_excel(archivo)
            df_procesado = procesar_dataframe(df, nombre_base)
            if df_procesado is not None:
                todos_los_dataframes.append(df_procesado)
                
        # CASO 3: Es CSV o TXT
        else:
            df = None
            for sep in [',', ';', '|', '\t']:
                for enc in ['latin-1', 'utf-8']:
                    try:
                        df_temp = pd.read_csv(archivo, low_memory=False, sep=sep, encoding=enc, on_bad_lines='skip')
                        if 'DPTO' in df_temp.columns:
                            df = df_temp
                            break
                    except:
                        continue
                if df is not None:
                    break
            
            df_procesado = procesar_dataframe(df, nombre_base)
            if df_procesado is not None:
                todos_los_dataframes.append(df_procesado)
                
    except Exception as e:
        print(f"  ⚠️ Error leyendo {nombre_base}: {e}")

# --- CONSOLIDACIÓN FINAL ---
if todos_los_dataframes:
    print("\nConsolidando todos los datos...")
    df_consolidado = pd.concat(todos_los_dataframes, ignore_index=True)
    
    # Guardar Log
    df_log = pd.DataFrame(registro_limpieza)
    df_log.to_csv(LOG_PATH, index=False, encoding='utf-8-sig')
    
    # Limpieza de la columna 'PER' (Año)
    if 'PER' in df_consolidado.columns:
        df_consolidado['PER'] = pd.to_numeric(df_consolidado['PER'], errors='coerce')
        def extraer_anio(nombre):
            for palabra in str(nombre).replace('-', ' ').replace('_', ' ').split():
                if palabra.isdigit() and len(palabra) == 4:
                    return int(palabra)
            return np.nan
        df_consolidado['PER'] = df_consolidado['PER'].fillna(df_consolidado['archivo_origen'].apply(extraer_anio))
            
    df_consolidado.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ Dataset guardado en: {OUTPUT_PATH}")
    print(f"✅ Total registros de Pasto: {len(df_consolidado)}")
    print(f"✅ Log de limpieza guardado en: {LOG_PATH}")
    
    print("\n--- RESUMEN POR AÑO (Columna PER) ---")
    if 'PER' in df_consolidado.columns:
        print(df_consolidado['PER'].value_counts().sort_index())
else:
    print("\n❌ No se encontraron datos válidos de Pasto en los archivos.")