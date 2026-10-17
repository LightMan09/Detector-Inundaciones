import shutil                          # para copiar archivos
from pathlib import Path               # rutas cómodas en Windows
from collections import Counter, defaultdict  # conteos

BASE = Path(__file__).parent                  # carpeta dataser (donde está este script)
DESTINO = BASE / "dataset_sapo_v2"            # dataset fusionado nuevo
ORIGENES = {                                  # carpeta de origen -> id de clase final
    "dataset_limpio": 0,
    "dataset_tapado": 1,
    "dataset_inundado": 2,
}
NOMBRES = {0: "limpia", 1: "tapada", 2: "con_agua"}   # nombres de clase finales
SPLITS = {"train": "train", "valid": "val", "val": "val", "test": "test"}  # acepta 'valid' y 'val' y los unifica en 'val'
EXT = {".jpg", ".jpeg", ".png"}               # extensiones de imagen válidas

for split in ("train", "val", "test"):        # creamos la estructura final
    (DESTINO / "images" / split).mkdir(parents=True, exist_ok=True)
    (DESTINO / "labels" / split).mkdir(parents=True, exist_ok=True)

cajas = {s: Counter() for s in ("train", "val", "test")}   # cajas por split y clase
imgs_total = Counter()                                      # imágenes por split
bases_por_split = defaultdict(set)                          # nombres base por split (para detectar fugas)

for origen, nuevo_id in ORIGENES.items():                   # recorremos cada dataset de origen
    raiz = BASE / origen
    if not raiz.exists():                                   # si falta la carpeta, avisamos fuerte
        print(f"!! NO EXISTE {origen}")
        continue
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir()):   # recorremos las carpetas que EXISTEN
        if carpeta.name not in SPLITS:                      # carpeta desconocida: avisamos, no la ignoramos en silencio
            print(f"!! carpeta desconocida en {origen}: {carpeta.name}")
            continue
        destino_split = SPLITS[carpeta.name]                # 'valid' o 'val' -> 'val'
        ruta_img, ruta_lbl = carpeta / "images", carpeta / "labels"
        if not ruta_img.exists():                           # estructura inesperada: avisamos
            print(f"!! {origen}/{carpeta.name} no tiene carpeta images")
            continue
        for img in ruta_img.iterdir():                      # recorremos las imágenes
            if img.suffix.lower() not in EXT:               # saltamos archivos que no son imagen
                continue
            nombre_nuevo = f"{nuevo_id}_{img.name}"         # prefijo para evitar nombres repetidos entre datasets
            shutil.copy2(img, DESTINO / "images" / destino_split / nombre_nuevo)   # copiamos la imagen
            imgs_total[destino_split] += 1
            bases_por_split[destino_split].add(f"{nuevo_id}_" + img.name.split(".rf.")[0])  # base sin el hash de Roboflow
            txt = ruta_lbl / (img.stem + ".txt")            # su etiqueta original
            salida = DESTINO / "labels" / destino_split / f"{nuevo_id}_{img.stem}.txt"
            if txt.exists():                                # si hay etiqueta, reasignamos el id
                lineas = []
                for l in txt.read_text().splitlines():
                    p = l.split()
                    if p:                                   # ignoramos líneas vacías
                        p[0] = str(nuevo_id)                # cambiamos el id 0 por el id final
                        lineas.append(" ".join(p))
                        cajas[destino_split][nuevo_id] += 1
                salida.write_text("\n".join(lineas) + ("\n" if lineas else ""))   # puede quedar vacío (imagen de fondo)
            else:
                salida.write_text("")                       # sin etiqueta = imagen de fondo, archivo vacío

yaml_txt = (                                                # data.yaml del dataset nuevo
    f"path: {DESTINO.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n"
    + "".join(f"  {i}: {n}\n" for i, n in NOMBRES.items())
)
(DESTINO / "data.yaml").write_text(yaml_txt, encoding="utf-8")

print("\n=== RESUMEN ===")
for s in ("train", "val", "test"):                          # resumen por split
    print(f"[{s}] imágenes: {imgs_total[s]} | " + " | ".join(f"{NOMBRES[i]}: {cajas[s][i]}" for i in NOMBRES))

print("\n=== POSIBLE FUGA ENTRE SPLITS (misma foto base en dos splits) ===")
for a, b in (("train", "val"), ("train", "test"), ("val", "test")):    # comparamos pares de splits
    comunes = bases_por_split[a] & bases_por_split[b]                   # nombres base repetidos
    print(f"{a} vs {b}: {len(comunes)} repetidos")