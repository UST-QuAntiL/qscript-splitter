
# qscript-splitter
Dieses Repository beinhaltet die Implementierung der Masterarbeit "Automatisierten Generierung von Quantum Workflows".

Der hier implementierte Algorithmus kann entweder alleine oder zusammen mit dem [QuantME-Modeling and Transformation Framework](https://github.com/UST-QuAntiL/QuantME-TransformationFramework) verwendet werden.
Wird der Algorithmus alleine Ausgeführt, so werden eingegebene Quantum Skripts aufgeteilt und die entstandenen Teile anschließend in einzelnen Dateien gespeichert.
Zusammen mit dem QuantME-Modeling and Transformation Framework werden zusätzlich Workflow Elemente generiert und mit den entsprechend generierten Teilen verbunden.

### Set Up (Algorithmus alleine)
Spezifiziere Input:
- In `testMain.py` wird eine Input-Datei definiert (Zeile 11).
- Per Default wird die Eingabe innerhalb der Datei `../qscript-splitter/Example/exampleScript.py` erwartet.
⇒ Plaziere Input Datei entsprechend.

Führe das Python-Script  `testMain.py` aus.
⇒ Die Ausgabe des Algorithmus befindet sich schließlich in den Dateien
`../qscript-splitter/Example/**part.py`.

### Set Up (inklusive QuantME-Modeling and Transformation Framework)
Installiere QuantME-Modeling and Transformation Framework.
Anleitung: https://github.com/UST-QuAntiL/QuantME-TransformationFramework/tree/develop/docs 

Füge Plugin Hinzu:
- Erstelle einen neuen Ordner mit dem Name `scriptSplitter` unter 
`../QuantME-TransformationFramework/resources/plugins/QuantME-CamundaPlugin`
- Kopiere die Dateien von `qscript-splitter/CamundaPluginFiles` in den neuen Ordner.
- Erstelle neuen Build `npm run build` 

Konfiguriere Plugin:
- In der vorher kopierten Datei `../ScriptSplitterPlugin.js` befindet sich die Funktion `getInput()`.
- Hier werden URL und fileName spezifiziert.
⇒ URL: URL der aktiven Flask App 
⇒ fileName: Input-Datei, default siehe oben (Algorithmus alleine).


Installiere [Flask](https://flask.palletsprojects.com/en/2.0.x/).
Anleitung: https://flask.palletsprojects.com/en/2.0.x/installation/

Starte Flask-App:
```perl
# setze Einstiegspunkt (BASH)  
export FLASP_APP=main
# setze Einstiegspunkt (CMD)
set FLASP_APP=main
# starte flask
flask run
```

Starte QuantME-Modeling and Transformation Framework (inkl. Plugin), z.B. mit  `npm run dev`.

Der Algorithmus kann jetzt über die Toolbar in der GUI gestartet werden.
⇒ Button "Start Splitting"

**Ergebnis:**
Zerlegt die (default) Datei in drei Teile und speichert diese unter `../qscript-splitter/Example/**part.py`.
Ein Workflow wird generiert.
Der Workflow enthält drei (External-)Service-Tasks mit einer jeweils zufälligen Topic.
Unter `../qscript-splitter/Example/` stehen Polling-Agents für jeden Service-Task bereit.
Die Polling-Agents müssen manuell konfiguriert werden.
Beim Start über die Kommando-Zeile können Camunda-Endpoint (Arg[1]) und Topic (Arg[2]) spezifiziert werden.

### Anmerkung
Dies ist eine prototypische Implementierung.
Die einzelnen Komponeten stellen keine ausgereifte Software-Lösung dar.

### Lizenz
[Apache-2.0 License](https://github.com/UST-QuAntiL/qscript-splitter/blob/main/LICENSE)







