# Phantasmagoria – Sottotitoli in italiano

Sottotitoli italiani (fan-made) per **Phantasmagoria** (Sierra, 1995), da usare con [ScummVM](https://www.scummvm.org/).

Il gioco è solo in inglese parlato e non ha sottotitoli. Questo progetto copre tutto il parlato:

| Cosa | File | Sottotitoli | Serve ScummVM con patch? |
|---|---|---|---|
| Filmati a schermo intero (VMD) | `srt/VMD` | 47 | No, funziona con ScummVM normale |
| Personaggi nelle stanze (Robot, RBT) | `srt/ROBOT` | 488 | **Sì** |
| Teschio dei suggerimenti, oggetti dell'inventario (RESOURCE.AUD) | `srt/AUD` | 111 | **Sì** |

Circa 1900 battute, trascritte con Whisper e tradotte in italiano.

Versione italiana di Phantasmagoria 2: [phantasmagoria2-sottotitoli-ita](https://github.com/JoJoD3v/phantasmagoria2-sottotitoli-ita).

## Requisiti

- Phantasmagoria (testato sulla versione Steam, DOS/English)
- ScummVM **con la patch di questa repo** per personaggi e teschio (vedi sotto).
  Con ScummVM normale vedrai solo i sottotitoli dei filmati.

## Installazione

1. Scarica la repo (**Code → Download ZIP**) ed estraila.
2. Tasto destro su `install.ps1` → **Esegui con PowerShell**.
   Lo script trova da solo il gioco nelle librerie Steam; altrimenti chiede il percorso.

```powershell
.\install.ps1 -GamePath "C:\Giochi\Phantasmagoria"
```

Se Windows blocca lo script ("esecuzione di script disabilitata"):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

A mano: `srt/VMD/*` → `Phant\VMD`, `srt/ROBOT/*` → `Phant\ROBOT`, `srt/AUD/*` → `Phant`.

Disinstallazione: `.\install.ps1 -Uninstall`

## ScummVM con la patch

ScummVM di serie carica i file `.srt` solo per i filmati. La patch in `scummvm/sci-fan-subtitles.patch` (motore SCI, ~100 righe) aggiunge:

- `<n>.rbt.srt` per i Robot: il testo appare nella parte bassa della scena, mouse e cursore restano al gioco;
- `<mappa>-<tupla>.a36.srt` / `<n>.aud.srt` per il parlato di `RESOURCE.AUD`, sincronizzato con la clip.

Una build per Windows è nelle **Releases** di questa repo (se presente). Per compilarla da soli (MSYS2 / MinGW64):

```bash
git clone https://github.com/scummvm/scummvm.git && cd scummvm
git checkout $(cat ../scummvm/BASE_COMMIT.txt)   # opzionale: commit su cui è stata fatta la patch
git apply ../scummvm/sci-fan-subtitles.patch
./configure --disable-all-engines --enable-engine=sci,sci32 --enable-release
make -j$(nproc)
```

Il `scummvm.exe` risultante usa la stessa configurazione e gli stessi salvataggi dello ScummVM installato.

### Impostazioni

In **Opzioni del gioco → Motore** lascia spento *Enable black-lined video*.

## Limiti

- Trascrizione automatica: qualche nome o frase sussurrata può essere imprecisa. Segnalazioni e correzioni benvenute (issue o pull request).
- I sottotitoli dei Robot sono spezzati per pause e lunghezza, non sempre per frase.

## Correggere una battuta

Le traduzioni stanno in `data/translations/it_{vmd,rbt_*,aud}.json` (`id → [battute]`, stesso ordine di `data/en_*/<id>.json`, che contiene testo inglese e tempi). Poi:

```bash
python tools/build_srt.py
```

## Rifare tutto da zero

```bash
# audio dei filmati (ffmpeg legge i VMD)
for f in Phant/VMD/*.VMD; do ffmpeg -i "$f" -vn -ac 1 -ar 16000 "wav_vmd/$(basename "${f%.*}").wav"; done
# audio dei Robot (formato Sierra, estrattore incluso)
python tools/rbt_audio.py Phant/ROBOT wav_rbt
# parlato di RESOURCE.AUD (legge le mappe audio del gioco)
python tools/aud_extract.py Phant wav_aud
```

Poi trascrivi ogni cartella con `tools/transcribe.py` ([faster-whisper](https://github.com/SYSTRAN/faster-whisper) large-v3; legge `wav/` e scrive `data/en/`, rinomina in `en_vmd` / `en_rbt` / `en_aud`), traduci in `data/translations/` e lancia `tools/build_srt.py`.

## Note legali

Progetto amatoriale non affiliato a Sierra / Activision. Non contiene file del gioco: serve una copia originale.
Phantasmagoria e i suoi dialoghi sono proprietà dei rispettivi titolari.
Gli script sono rilasciati con licenza MIT; la patch per ScummVM è sotto GPL v3 come ScummVM.
