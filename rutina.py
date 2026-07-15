# rutina.py — contingut estàtic del pla

FOAM = [
    {"zona": "TFL (2 dits sota la cresta ilíaca, davant-lateral)", "dosi": "60 s/costat", "nota": "Pressió sostinguda"},
    {"zona": "Gluti mitjà", "dosi": "45 s/costat", "nota": "Roller o pilota"},
    {"zona": "Vast lateral", "dosi": "45 s/costat", "nota": "Cadena lateral"},
]

DINAMIC = [
    {"exercici": "90/90 hip switch", "dosi": "10 canvis/costat", "nota": "Rotació de maluc"},
    {"exercici": "Couch stretch dinàmic", "dosi": "8 pulsacions/costat", "nota": "Gluti contret, no arquegis lumbars"},
    {"exercici": "World's greatest stretch", "dosi": "5/costat", "nota": "Amb rotació cap al sostre"},
    {"exercici": "Rotació toràcica quadrupèdia", "dosi": "8/costat", "nota": "Mà al clatell, obre el pit"},
    {"exercici": "Squat prying (goblet)", "dosi": "45 s", "nota": "Colzes empenyent genolls"},
    {"exercici": "Balanceig de cama frontal i lateral", "dosi": "12/direcció/cama", "nota": "Sense rebot"},
]

MINIBANDS = [
    {"exercici": "Monster walk lateral (banda 5 kg)", "dosi": "2x15 passos/direcció", "nota": "Gluti mitjà"},
    {"exercici": "Clamshell amb pausa 2s (banda 6 kg)", "dosi": "2x12/costat", "nota": "Rotadors externs"},
    {"exercici": "Pont de gluti amb abducció", "dosi": "2x15", "nota": "Gluti major + mitjà"},
    {"exercici": "Copenhagen plank (regressió: genoll)", "dosi": "2x20 s/costat", "nota": "Adductors"},
]

PASSIVA = [
    {"posició": "Couch stretch (genoll a la paret)", "temps": "120 s/costat", "clau": "EL TEU #1. Retroversió pèlvica, gluti contret"},
    {"posició": "Pigeon pose (o figura-4 estirat)", "temps": "120 s/costat", "clau": "Si el genoll molesta, figura-4 al terra"},
    {"posició": "Estirament BIT modificat (cama creuada + inclinació lateral)", "temps": "90 s/costat", "clau": "De peu, cama afectada darrere"},
    {"posició": "Papallona asseguda + inclinació", "temps": "90 s", "clau": "Colzes als genolls, esquena llarga"},
    {"posició": "Isquios amb banda estirat", "temps": "90 s/costat", "clau": "Cama recta, l'altra al terra"},
    {"posició": "Postura del nen amb rotació", "temps": "60 s/costat", "clau": "Braç per sota del cos"},
    {"posició": "Respiració 90/90 (cames sobre banc)", "temps": "10 respiracions 4-7-8", "clau": "Baixa el to simpàtic → Recovery"},
]

MICRO = [
    {"quan": "Cada 90 min d'estudi/ordinador", "què": "30 s couch stretch/costat + 10 rotacions toràciques"},
    {"quan": "Post-bici (obligatori)", "què": "90 s couch stretch/costat"},
    {"quan": "Abans de dormir", "què": "60 s pigeon/costat"},
]

FORCA_A = [
    {"patró": "Front Squat", "casa": "Goblet squat / Front squat amb manuelles", "apart": "Squat a barra guiada o premsa", "sr": "4 x 8-10", "tempo": "3-1-1-0"},
    {"patró": "Tracció vertical", "casa": "Dominades (llastrades si >10 reps)", "apart": "Poliada alta (pull-down)", "sr": "4 x 6-8", "tempo": "2-0-1-1"},
    {"patró": "Empenta horitzontal", "casa": "Press banca amb manuelles", "apart": "Press pectoral a màquina", "sr": "4 x 8-10", "tempo": "3-0-1-0"},
    {"patró": "Accessori quàdriceps", "casa": "Bulgarian split squat", "apart": "Bulgarian split squat (peu al banc)", "sr": "3 x 10/cama", "tempo": "2-0-1-0"},
    {"patró": "Core anti-extensió", "casa": "Roda abdominal (des de genolls)", "apart": "Roda abdominal", "sr": "3 x 8-12", "tempo": "Controlat"},
    {"patró": "Prevenció BIT", "casa": "Abducció de maluc de peu amb banda llarga", "apart": "Idem", "sr": "2 x 20/costat", "tempo": "Continu"},
]

FORCA_B = [
    {"patró": "Hip Hinge", "casa": "Pes mort romanès amb manuelles", "apart": "RDL a barra guiada o poliada baixa", "sr": "4 x 8-10", "tempo": "3-1-1-0"},
    {"patró": "Empenta vertical", "casa": "Press militar assegut amb manuelles", "apart": "Press militar a màquina", "sr": "4 x 8-10", "tempo": "2-0-1-0"},
    {"patró": "Tracció horitzontal", "casa": "Rem a una mà amb manuella (suport banc)", "apart": "Rem baix a poliada", "sr": "4 x 10", "tempo": "2-1-1-0"},
    {"patró": "Cadena posterior", "casa": "Hip thrust amb manuella al maluc", "apart": "Hip thrust amb banda + suport", "sr": "3 x 12", "tempo": "2-2-1-0"},
    {"patró": "Isquios", "casa": "Nòrdic curl excèntric o curl femoral amb banda", "apart": "Curl femoral a màquina", "sr": "3 x 6-8", "tempo": "4-0-1-0"},
    {"patró": "Core anti-rotació", "casa": "Pallof press amb banda llarga", "apart": "Pallof press a poliada", "sr": "3 x 12/costat", "tempo": "2-2-2-0"},
]

FORCA_C = [
    {"patró": "Unilateral quàdriceps", "casa": "Step-up al banc amb manuelles", "apart": "Step-up al banc", "sr": "4 x 10/cama", "tempo": "2-0-1-0"},
    {"patró": "Unilateral hinge", "casa": "Pes mort a una cama amb manuella", "apart": "Idem amb poliada baixa", "sr": "3 x 10/cama", "tempo": "3-0-1-0"},
    {"patró": "Tracció vertical (variant)", "casa": "Dominades supinació (chin-up)", "apart": "Pull-down supinació", "sr": "3 x 8-10", "tempo": "2-0-1-1"},
    {"patró": "Empenta (variant)", "casa": "Press inclinat amb manuelles", "apart": "Press inclinat a màquina", "sr": "3 x 10", "tempo": "2-0-1-0"},
    {"patró": "Core dens (circuit)", "casa": "Hollow hold 30s → Dead bug 12/costat → Plancha lateral 30s/costat", "apart": "Idem", "sr": "3 voltes", "tempo": "—"},
    {"patró": "Condicional (sense impacte)", "casa": "Corda de saltar SI tolerància OK — si no: bici", "apart": "Idem", "sr": "6 x 45s / 15s off", "tempo": "—"},
]

DIES = {
    0: {"nom": "Dilluns", "tipus": "forca", "titol": "FORÇA A", "sub": "Squat dominant",
        "exercicis": FORCA_A, "extra": "Escalfament complet (10 min) abans de començar."},
    1: {"nom": "Dimarts", "tipus": "passiva", "titol": "DESCANS · Mobilitat passiva", "sub": "18 min",
        "extra": "Al final del dia o post-activitat lleugera. Mai en fred: 3 min de bici o saltar suau abans."},
    2: {"nom": "Dimecres", "tipus": "forca", "titol": "FORÇA B", "sub": "Hinge dominant",
        "exercicis": FORCA_B, "extra": "Afegeix 30 s de dead hang a la barra abans de començar."},
    3: {"nom": "Dijous", "tipus": "micro", "titol": "DESCANS · Micro-dosi ampliada", "sub": "5 min",
        "extra": "Couch stretch 90 s/costat + Pigeon 90 s/costat."},
    4: {"nom": "Divendres", "tipus": "forca", "titol": "FORÇA C", "sub": "Mixt / unilateral / densitat",
        "exercicis": FORCA_C, "extra": "Escalfament complet (10 min) abans de començar."},
    5: {"nom": "Dissabte", "tipus": "micro", "titol": "ACTIVITAT · Bici / pàdel / natació", "sub": "Post-activitat: 5 min",
        "extra": "Post-activitat OBLIGATORI: couch stretch 90 s/costat + pigeon 60 s/costat."},
    6: {"nom": "Diumenge", "tipus": "passiva", "titol": "DESCANS · Mobilitat passiva", "sub": "18 min",
        "extra": "El bloc llarg de la setmana. Aprofita per fer l'escalivada i l'export de dades."},
}

DESCANSOS = [
    {"tipus": "Bàsics (squat, RDL, dominades, press)", "descans": "2-3 min"},
    {"tipus": "Accessoris (bulgarian, hip thrust, rem)", "descans": "90 s"},
    {"tipus": "Core / prevenció", "descans": "45-60 s"},
]
