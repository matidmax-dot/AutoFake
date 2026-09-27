import os
import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

DB_PATH = '/content/vehiculos.db'

@app.get("/", response_class=HTMLResponse)
def index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Archivo index.html no encontrado</h1>"

@app.get("/api/buscar/{patente}")
def buscar_patente(patente: str):
    patente = patente.upper().strip()
    
    if not os.path.exists(DB_PATH):
        return JSONResponse(content={"error": "Base de datos no encontrada"}, status_code=404)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Consultar ficha del vehículo (incluyendo marca y modelo)
    cursor.execute("SELECT marca, modelo, ano, num_motor, num_chasis FROM vehiculos WHERE patente = ?", (patente,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return JSONResponse(content={"error": "Patente no encontrada"}, status_code=404)
        
    marca, modelo, ano, num_motor, num_chasis = row
    
    # 2. Consultar historial de revisiones
    cursor.execute("SELECT fecha, planta, certificado, kilometraje, resultado FROM revisiones WHERE patente = ? ORDER BY fecha DESC", (patente,))
    revisiones_raw = cursor.fetchall()
    conn.close()
    
    historial = []
    aprobadas = 0
    rechazadas = 0
    
    for r in revisiones_raw:
        fecha, planta, certificado, km, res = r
        if "APROBADO" in str(res).upper():
            aprobadas += 1
        else:
            rechazadas += 1
            
        historial.append({
            "fecha": fecha,
            "planta": planta,
            "certificado": certificado,
            "kilometraje": km,
            "resultado": res
        })
        
    total = aprobadas + rechazadas
    tasa_aprobacion = round((aprobadas / total * 100), 1) if total > 0 else 0
    
    # 3. Detectar anomalías en odómetro
    alertas = []
    for i in range(len(historial) - 1):
        km_reciente = historial[i]["kilometraje"]
        km_antiguo = historial[i+1]["kilometraje"]
        if km_reciente < km_antiguo:
            diferencia = km_antiguo - km_reciente
            alertas.append({
                "mensaje": f"Kilometraje disminuyó en {diferencia:,} km entre {historial[i]['fecha']} ({km_reciente:,} km) y {historial[i+1]['fecha']} ({km_antiguo:,} km)."
            })

    return {
        "ppu": patente,
        "info_vehiculo": {
            "marca": marca,
            "modelo": modelo,  # Modelo del vehículo expuesto en API
            "ano": ano,
            "num_motor": num_motor,
            "num_chasis": num_chasis
        },
        "aprobadas": aprobadas,
        "rechazadas": rechazadas,
        "tasa_aprobacion": tasa_aprobacion,
        "alertas": alertas,
        "historial": historial
    }
